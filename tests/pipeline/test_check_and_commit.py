import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.pipeline.models import ActionCandidate, CheckResult
from living_narrative.state.models import Event, Visibility


def _error_check(context, narration_text, resolved_events, diff_candidate):
    return [CheckResult(severity="error", message="boom")]


def test_check_error_stops_for_review_regardless_of_commit_mode(tmp_path, build_project):
    project_path = build_project(tmp_path)
    registry = default_registry()
    registry.register("check", _error_check)

    result = TurnPipeline(registry=registry).run(project_path, commit_mode="auto")

    assert result.status == TurnStatus.STOPPED_FOR_REVIEW
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    assert state_diff["applied"] is False


def test_commit_mode_auto_applies_and_review_defers(tmp_path, build_project):
    project_auto = build_project(tmp_path / "auto")
    project_review = build_project(tmp_path / "review")

    result_auto = TurnPipeline().run(project_auto, commit_mode="auto")
    result_review = TurnPipeline().run(project_review, commit_mode="review")

    assert result_auto.status == TurnStatus.APPLIED
    assert result_review.status == TurnStatus.PENDING_REVIEW

    diff_auto = yaml.safe_load(
        (result_auto.turn_dir / "state_diff.yaml").read_text(encoding="utf-8")
    )
    diff_review = yaml.safe_load(
        (result_review.turn_dir / "state_diff.yaml").read_text(encoding="utf-8")
    )
    assert diff_auto["applied"] is True
    assert diff_review["applied"] is False


def test_pacing_stall_warn_does_not_block_auto_apply(tmp_path, build_project):
    """Issue 011: with no threats/scene-transitions ever firing, a story with pacing turned
    on stalls quickly; the pacing checker's warn must not stop auto-apply."""
    project_path = build_project(tmp_path, pacing={"stall_window": 1, "pressure_boost": 4})
    pipeline = TurnPipeline()

    pipeline.run(project_path, commit_mode="auto")  # turn 1: too early to judge (turn <= window)
    result = pipeline.run(project_path, commit_mode="auto")  # turn 2: stalled

    assert result.status == TurnStatus.APPLIED
    checks = yaml.safe_load((result.turn_dir / "checks.yaml").read_text(encoding="utf-8"))
    findings = checks["findings"] if isinstance(checks, dict) else checks
    pacing_findings = [f for f in findings if f["source"] == "pacing_check"]
    assert pacing_findings
    assert pacing_findings[0]["severity"] == "warn"


def test_speech_register_warn_does_not_block_auto_apply(tmp_path, build_project):
    """Issue 012: a dialogue event using one of the character's own forbidden_terms
    (e.g. the wrong first-person pronoun) is only a warn -- auto-apply still commits."""
    project_path = build_project(
        tmp_path, speech={"first_person": "私", "forbidden_terms": ["僕", "俺"]}
    )
    registry = default_registry()

    def _resolve_with_forbidden_term_dialogue(
        context, world_events, action_candidates, allocate_event_id, record_roll
    ):
        return [
            Event(
                id=allocate_event_id(),
                turn=context.turn,
                type="character_dialogue",
                text="僕はここにいる",
                visibility=Visibility.READER,
                effects={"character_id": "char_001"},
            )
        ]

    registry.register("resolve", _resolve_with_forbidden_term_dialogue)

    result = TurnPipeline(registry=registry).run(project_path, commit_mode="auto")

    assert result.status == TurnStatus.APPLIED
    checks = yaml.safe_load((result.turn_dir / "checks.yaml").read_text(encoding="utf-8"))
    findings = checks["findings"] if isinstance(checks, dict) else checks
    speech_findings = [f for f in findings if f["source"] == "speech_register_check"]
    assert speech_findings
    assert speech_findings[0]["severity"] == "warn"
    assert speech_findings[0]["related_ids"] == ["event_0001"]


def test_character_consistency_warn_does_not_block_auto_apply(tmp_path, build_project):
    """Issue 016: a dialogue event where the speaker mentions something they don't know is
    only a warn -- auto-apply still commits."""
    project_path = build_project(tmp_path, knowledge={"does_not_know": ["封印施設"]})
    registry = default_registry()

    def _resolve_with_know_violation_dialogue(
        context, world_events, action_candidates, allocate_event_id, record_roll
    ):
        return [
            Event(
                id=allocate_event_id(),
                turn=context.turn,
                type="character_dialogue",
                text="封印施設のことは聞いたことがある",
                visibility=Visibility.READER,
                effects={"character_id": "char_001"},
            )
        ]

    registry.register("resolve", _resolve_with_know_violation_dialogue)

    result = TurnPipeline(registry=registry).run(project_path, commit_mode="auto")

    assert result.status == TurnStatus.APPLIED
    checks = yaml.safe_load((result.turn_dir / "checks.yaml").read_text(encoding="utf-8"))
    findings = checks["findings"] if isinstance(checks, dict) else checks
    consistency_findings = [f for f in findings if f["source"] == "character_consistency_check"]
    assert consistency_findings
    assert consistency_findings[0]["severity"] == "warn"
    assert consistency_findings[0]["related_ids"] == ["event_0001"]


def test_life_or_death_combat_failure_stops_for_review_without_auto_death(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    attacker_path = state_dir / "characters" / "char_001.yaml"
    attacker = yaml.safe_load(attacker_path.read_text(encoding="utf-8"))
    attacker["stats"] = {"strength": -100, "hp": 10}
    attacker_path.write_text(yaml.safe_dump(attacker, allow_unicode=True), encoding="utf-8")
    (state_dir / "characters" / "char_002.yaml").write_text(
        yaml.safe_dump(
            {"id": "char_002", "name": "敵", "role": "guard", "stats": {"hp": 10}},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    scene_path = state_dir / "scenes" / "scene_001.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["active_characters"].append("char_002")
    scene_path.write_text(yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8")
    registry = default_registry()

    def combat_act(context, world_events, gateway, interventions, **kwargs):
        return [
            ActionCandidate(
                character_id="char_001",
                action_text="決死の一撃を放つ",
                target_id="char_002",
                effects={
                    "combat": {
                        "attacker": "char_001",
                        "defender": "char_002",
                        "stakes": "仲間を逃がす",
                        "stat": "strength",
                        "target": 0,
                        "damage": 4,
                        "life_or_death": True,
                    }
                },
            )
        ], []

    registry.register("act", combat_act)

    result = TurnPipeline(registry=registry).run(project_path, commit_mode="auto")

    assert result.status == TurnStatus.STOPPED_FOR_REVIEW
    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    combat_roll = next(roll for roll in rolls if roll["label"] == "combat:char_001:char_002")
    combat_event = next(event for event in events if event["type"] == "combat")
    assert combat_roll["outcome"] == "failure"
    assert combat_roll["severity"] == "critical"
    assert combat_event["roll_ids"] == [combat_roll["id"]]
    assert all(change.get("path") != "status" for change in diff["diff"]["changes"])


def test_invalid_combat_is_audited_without_blocking_valid_combat_pipeline(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    attacker_path = state_dir / "characters" / "char_001.yaml"
    attacker = yaml.safe_load(attacker_path.read_text(encoding="utf-8"))
    attacker["stats"] = {"strength": 10, "hp": 10}
    attacker_path.write_text(yaml.safe_dump(attacker, allow_unicode=True), encoding="utf-8")
    (state_dir / "characters" / "char_002.yaml").write_text(
        yaml.safe_dump(
            {"id": "char_002", "name": "敵", "role": "guard", "stats": {"hp": 10}},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    scene_path = state_dir / "scenes" / "scene_001.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["active_characters"].append("char_002")
    scene_path.write_text(yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8")
    registry = default_registry()

    def mixed_combat_act(context, world_events, gateway, interventions, **kwargs):
        def candidate(defender, stakes):
            return ActionCandidate(
                character_id="char_001",
                action_text=stakes,
                target_id=defender,
                effects={
                    "combat": {
                        "attacker": "char_001",
                        "defender": defender,
                        "stakes": stakes,
                        "stat": "strength",
                        "target": 100,
                        "damage": 4,
                    }
                },
            )

        return [candidate("char_999", "不正な攻撃"), candidate("char_002", "有効な攻撃")], []

    registry.register("act", mixed_combat_act)

    result = TurnPipeline(registry=registry).run(project_path, commit_mode="auto")

    assert result.status != TurnStatus.FAILED
    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    combat_events = [event for event in events if event["type"].startswith("combat")]
    assert [event["type"] for event in combat_events] == ["combat_rejected", "combat"]
    assert combat_events[0]["visibility"] == "gm_only"
    assert len([roll for roll in rolls if roll["label"].startswith("combat:")]) == 1
    hp_change = next(change for change in diff["diff"]["changes"] if change["path"] == "stats.hp")
    assert hp_change["id"] == "char_002"
    assert hp_change["value"] == -4
