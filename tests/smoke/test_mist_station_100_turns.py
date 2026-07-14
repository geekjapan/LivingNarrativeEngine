"""Issue 071: ADR-0010's 100-turn mock journey is a permanent CI gate."""

from datetime import UTC, datetime
from pathlib import Path

import yaml

from living_narrative.agents.character import run_character_agent
from living_narrative.export_replay import assemble_replay
from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.pipeline.models import ActionCandidate
from living_narrative.session.metrics import collect_metrics
from living_narrative.session.resume import restore_resume_state
from living_narrative.session.review import ReviewDecision, resolve_review
from living_narrative.session.rollback import (
    copy_project_for_branch,
    execute_rollback,
    plan_rollback,
)
from living_narrative.state.store import StateStore
from living_narrative.workspace.backup import create_backup, restore_backup
from living_narrative.workspace.init import create_project
from living_narrative.workspace.loader import load_project

FIXED_SEED = "issue-071-mock-journey-fixed-seed"
CHECKPOINT_TURN = 40
TURN_COUNT = 100


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _prepare_project(project_dir: Path) -> Path:
    project_path = create_project(project_dir, title="霧の駅", template="mist_station")
    project = _load_yaml(project_path)
    project.update(
        {
            "random_seed": FIXED_SEED,
            "user_mode": "full_gm",
        }
    )
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    state_dir = project_path.parent / "workspace" / "state"
    for character_id in ("char_001", "char_002"):
        character_path = state_dir / "characters" / f"{character_id}.yaml"
        character = _load_yaml(character_path)
        character.setdefault("stats", {})["hp"] = 10
        character_path.write_text(
            yaml.safe_dump(character, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    # Exercise the shipped Mist Station affordances first, then extend scene 2's authored
    # chain only far enough for this deliberately longer-than-product 100-turn soak.
    fallback_count = (TURN_COUNT - 1) // 3
    scene_path = state_dir / "scenes" / "scene_002.yaml"
    scene = _load_yaml(scene_path)
    for index in range(fallback_count):
        previous_thread = f"thread_{index + 9:03d}"
        next_thread = f"thread_{index + 10:03d}"
        affordance_id = f"affordance_{index + 1000:04d}"
        scene["fallback_affordance_ids"].append(affordance_id)
        scene["affordances"].append(
            {
                "id": affordance_id,
                "text": f"手掛かり{index + 10}を確かめ、次の糸口へ進む",
                "visibility": "scene",
                "known_by": ["char_001", "char_002"],
                "actor_ids": ["char_001"],
                "prerequisites": {
                    "required_fact_ids": [],
                    "quest_statuses": {},
                    "thread_statuses": {previous_thread: "open"},
                },
                "success_chance": 100,
                "recurrence": "once",
                "used_event_ids": [],
                "exclusive": True,
                "fallback_only": True,
                "outcomes": [
                    {
                        "target": "threads",
                        "op": "set",
                        "path": "status",
                        "id": previous_thread,
                        "value": "resolved",
                        "visibility": "reader",
                    },
                    {
                        "target": "threads",
                        "op": "add",
                        "path": "",
                        "value": {
                            "id": next_thread,
                            "description": f"手掛かり{index + 10}の先にある安定した糸口",
                            "status": "open",
                            "related_event_ids": [],
                            "notes": [],
                            "opened_turn": 0,
                        },
                        "visibility": "reader",
                    },
                ],
            }
        )
    scene_path.write_text(
        yaml.safe_dump(scene, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return project_path


def _make_registry():
    registry = default_registry()

    def game_act(context, world_events, gateway, interventions, **kwargs):
        actions, records = run_character_agent(
            context, world_events, gateway, interventions, **kwargs
        )
        if context.turn == 1:
            actions.append(
                ActionCandidate(
                    character_id="char_001",
                    action_text="追跡者を退ける",
                    target_id="char_002",
                    effects={
                        "combat": {
                            "attacker": "char_001",
                            "defender": "char_002",
                            "stakes": "出口への退路を守る",
                            "stat": "体力",
                            "skill": "探索",
                            "target": 100,
                            "damage": 2,
                        }
                    },
                )
            )
        return actions, records

    registry.register("act", game_act)
    return registry


def _run_turn(pipeline, project_path: Path, turn: int, branch_label: str | None = None):
    drafts = [
        {
            "type": "character_directive",
            "target": {"kind": "character", "id": "char_001"},
            "content": f"ターン{turn}の出口探索を進める{branch_label or ''}",
            "constraints": {},
            "visibility": "character",
        }
    ]
    if turn == 1:
        drafts.append(
            {
                "type": "dice_roll_request",
                "target": {"kind": "character", "id": "char_001"},
                "content": "霧の切れ目を見抜く",
                "constraints": {"target": 100, "stat": "知力", "skill": "観察"},
                "visibility": "character",
            }
        )
    if turn % 3 == 0:
        drafts.append(
            {
                "type": "world_directive",
                "target": {"kind": "world"},
                "content": f"ターン{turn}の周囲を見渡す",
                "constraints": {},
                "visibility": "reader",
            }
        )

    result = pipeline.run(project_path, intervention_drafts=drafts)
    if result.status in (TurnStatus.STOPPED_FOR_REVIEW, TurnStatus.PENDING_REVIEW):
        paths = load_project(project_path).paths
        resolve_review(
            workspace_root=paths.root,
            state_dir=paths.state,
            turn_dir=result.turn_dir,
            decision=ReviewDecision.ACCEPT_ALL,
            decided_by="full_gm",
        )
    assert result.status != TurnStatus.FAILED, f"turn {turn} failed: {result.turn_dir}"
    return result


def _snapshot(project_path: Path) -> dict[Path, bytes]:
    root = project_path.parent / "workspace"
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root) != Path("interventions.yaml")
    }


def _artifact_fingerprint(project_path: Path) -> dict[str, str]:
    runs = project_path.parent / "workspace" / "runs"
    files = {}
    for turn_dir in sorted(runs.glob("turn_[0-9][0-9][0-9][0-9]")):
        for name in ("events.yaml", "rolls.yaml", "state_diff.yaml", "narration.md"):
            path = turn_dir / name
            if path.exists():
                files[str(path.relative_to(runs))] = path.read_text(encoding="utf-8")
    return files


def _live_events(project_path: Path) -> list[dict]:
    runs = project_path.parent / "workspace" / "runs"
    events = []
    for turn_dir in sorted(runs.glob("turn_[0-9][0-9][0-9][0-9]")):
        events.extend(_load_yaml(turn_dir / "events.yaml") or [])
    return events


def _run_journey(tmp_path: Path, name: str):
    project_path = _prepare_project(tmp_path / name)
    registry = _make_registry()
    pipeline = TurnPipeline(registry=registry)

    for turn in range(1, CHECKPOINT_TURN + 1):
        _run_turn(pipeline, project_path, turn)

    paths = load_project(project_path).paths
    checkpoint_replay = assemble_replay(paths.runs, style="novel")
    assert checkpoint_replay.strip()
    checkpoint_snapshot = _snapshot(project_path)
    checkpoint_state = (paths.state / "timeline.yaml").read_bytes()

    # Make a divergent turn, then exercise a copy/rollback branch and the main rollback path.
    original_turn_41 = _run_turn(pipeline, project_path, 41, "(main)")
    original_rolls = (original_turn_41.turn_dir / "rolls.yaml").read_text(encoding="utf-8")
    branch_path = copy_project_for_branch(project_path.parent, tmp_path / f"{name}-branch")
    branch_paths = load_project(branch_path).paths
    execute_rollback(branch_paths, plan_rollback(branch_paths.runs, CHECKPOINT_TURN))
    branch_turn = _run_turn(TurnPipeline(registry=registry), branch_path, 41, "(branch)")
    branch_intervention = _load_yaml(branch_turn.turn_dir / "intervention.yaml")
    assert any("(branch)" in item["content"] for item in branch_intervention["interventions"])

    main_paths = load_project(project_path).paths
    execute_rollback(main_paths, plan_rollback(main_paths.runs, CHECKPOINT_TURN))
    assert (main_paths.state / "timeline.yaml").read_bytes() == checkpoint_state
    assert (main_paths.runs / "turn_0041_rolledback_1").is_dir()
    for relative_path, content in checkpoint_snapshot.items():
        assert (project_path.parent / "workspace" / relative_path).read_bytes() == content

    rerun_turn_41 = _run_turn(TurnPipeline(registry=registry), project_path, 41, "(main)")
    rerun_rolls = (rerun_turn_41.turn_dir / "rolls.yaml").read_text(encoding="utf-8")
    assert yaml.safe_load(rerun_rolls) == yaml.safe_load(original_rolls)

    for turn in range(42, TURN_COUNT + 1):
        _run_turn(pipeline, project_path, turn)

    paths = load_project(project_path).paths
    final_replay = assemble_replay(paths.runs, style="novel")
    assert len(final_replay) > len(checkpoint_replay)
    metrics = collect_metrics(project_path)

    assert metrics.turns.total == TURN_COUNT
    assert metrics.turns.by_status == {"applied": TURN_COUNT}
    assert metrics.turns.rolledback == 1
    live_events = _live_events(project_path)
    assert not any(event.get("type") == "pacing_exhausted" for event in live_events)
    assert metrics.pacing.max_consecutive_stall_turns <= 3
    assert metrics.threads.opened > 0
    assert metrics.threads.resolved / metrics.threads.opened >= 0.5
    assert metrics.threads.max_open_turns is None or metrics.threads.max_open_turns <= 25
    assert metrics.checks.by_severity.get("critical", 0) == 0
    assert metrics.checks.by_severity.get("high", 0) == 0
    assert metrics.checks.by_source.get("leak", 0) == 0
    assert metrics.scenes.transition_count > 0 or any(
        event.get("type") == "action_outcome"
        and (event.get("effects") or {}).get("accepted")
        and (event.get("effects") or {}).get("advancement")
        for event in live_events
    )

    encounter_policies = {
        encounter.id: encounter
        for encounter in StateStore.load(load_project(project_path).paths.state).encounters
    }
    encounter_turns: dict[str, list[int]] = {}
    for event in live_events:
        if event.get("type") != "encounter":
            continue
        encounter_id = (event.get("effects") or {}).get("encounter_id")
        encounter_turns.setdefault(encounter_id, []).append(event.get("turn"))
    assert encounter_turns
    for encounter_id, turns in encounter_turns.items():
        policy = encounter_policies[encounter_id]
        if policy.recurrence == "once":
            assert len(turns) == 1
        else:
            assert all(right - left > 1 for left, right in zip(turns, turns[1:]))
    for character in metrics.emotions:
        for emotion in character.emotions:
            assert (
                emotion.max_consecutive_at_ceiling is None
                or emotion.max_consecutive_at_ceiling <= 5
            )
    assert (
        metrics.game.combat_count
        + metrics.game.quest_opened
        + metrics.game.applied_pc_action_count
        + metrics.game.encounter_count
        + metrics.game.skill_check_total
    ) > 0

    backup_root = create_backup(
        project_path,
        tmp_path / f"{name}-backups",
        created_at=datetime(2026, 7, 13, 0, 0, tzinfo=UTC),
    )
    restored_dir = tmp_path / f"{name}-restored"
    restore_backup(backup_root, restored_dir)
    restored_project = restored_dir / "project.yaml"
    resume = restore_resume_state(
        restored_dir / "workspace" / "runs", restored_dir / "interventions.yaml"
    )
    assert resume.last_applied_turn == TURN_COUNT
    assert resume.pending_review_turn is None
    resumed = _run_turn(TurnPipeline(registry=_make_registry()), restored_project, TURN_COUNT + 1)
    assert resumed.turn == TURN_COUNT + 1
    assert resumed.status != TurnStatus.FAILED

    return final_replay, _artifact_fingerprint(project_path)


def test_100_turn_mist_station_adr_0010_gate(tmp_path):
    replay_a, artifacts_a = _run_journey(tmp_path, "journey-a")
    replay_b, artifacts_b = _run_journey(tmp_path, "journey-b")

    assert replay_a == replay_b
    assert artifacts_a == artifacts_b
