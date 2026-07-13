"""Unit tests for ``session.metrics.collect_metrics`` (docs/issues/019).

Turn artifacts are hand-written directly (rather than produced by a real ``TurnPipeline``
run) so every number in ``ProjectMetrics`` can be hand-computed and asserted exactly --
the mock LLM provider (``llm/mock.py``) never fills optional structured-output fields
(``emotion_deltas``, ``thread_updates``, ``memory_summary_update``, ...), so a real mock run
never exercises the delta-reconstruction/thread/memory paths this module needs covered.
"""

from pathlib import Path

import yaml

from living_narrative.session.metrics import MetricsError, collect_metrics
from living_narrative.workspace.init import create_project

_STATE_FILES = {
    "world.yaml": {
        "id": "world_001",
        "name": "Test World",
        "summary": "A quiet test world.",
        "threats": [
            {
                "id": "threat_001",
                "name": "Something approaching",
                "pressure": 55,
                "pressure_per_turn": "1d6",
                "stages": [{"at": 50, "text": "stage fired", "visibility": "gm_only"}],
            }
        ],
    },
    "canon.yaml": [],
    "reader_state.yaml": [],
    "gm_vault.yaml": [],
    "relationships.yaml": [],
    "factions.yaml": [],
    "timeline.yaml": [
        {"turn": 1, "event_ids": ["event_0001"]},
        {"turn": 2, "event_ids": ["event_0002", "event_0003", "event_0004"]},
        {"turn": 3, "event_ids": ["event_0005"]},
    ],
    "unresolved_threads.yaml": [
        {
            "id": "thread_001",
            "description": "an open mystery",
            "status": "open",
            "opened_turn": 1,
        },
        {
            "id": "thread_002",
            "description": "a settled mystery",
            "status": "resolved",
            "opened_turn": 1,
        },
    ],
    "memory_summaries.yaml": [
        {"id": "memory_0001", "up_to_turn": 1, "text": "so far..."},
        {"id": "memory_0002", "up_to_turn": 2, "text": "and then..."},
    ],
}


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _build_hand_fixture(tmp_path: Path) -> Path:
    """A project whose state/turn artifacts are fully hand-written (see module docstring)."""
    project_path = create_project(tmp_path / "proj", title="metrics fixture", template="minimal")
    state_dir = project_path.parent / "workspace" / "state"

    for filename, data in _STATE_FILES.items():
        _write_yaml(state_dir / filename, data)

    _write_yaml(
        state_dir / "characters" / "char_001.yaml",
        {
            "id": "char_001",
            "name": "Aoi",
            "role": "detective",
            # fear has a baseline (trajectory reconstructable); calm does not (Issue 010
            # back-compat: decay/reconstruction only applies to emotions with a baseline).
            "emotions": {"fear": 100, "calm": 50},
            "emotions_baseline": {"fear": 20},
        },
    )
    _write_yaml(
        state_dir / "scenes" / "scene_001.yaml",
        {"id": "scene_001", "location": "station", "time": "night", "status": "ended"},
    )
    _write_yaml(
        state_dir / "scenes" / "scene_002.yaml",
        {"id": "scene_002", "location": "tunnel", "time": "night", "status": "active"},
    )

    runs_dir = project_path.parent / "workspace" / "runs"

    # Turn 1: emotion +50 (fear 20 -> 70), a thread opens, threat_001's first pressure roll.
    turn1 = runs_dir / "turn_0001"
    _write_yaml(turn1 / "meta.yaml", {"turn": 1, "status": "applied"})
    _write_yaml(
        turn1 / "state_diff.yaml",
        {
            "diff": {
                "id": "diff_0001",
                "turn": 1,
                "changes": [
                    {
                        "target": "character",
                        "op": "delta",
                        "path": "emotions.fear",
                        "value": 50,
                        "id": "char_001",
                        "visibility": "character",
                    },
                    {
                        "target": "quests",
                        "op": "add",
                        "path": "",
                        "value": {"id": "quest_001", "title": "出口", "status": "open"},
                        "visibility": "reader",
                    },
                ],
            },
            "applied": True,
            "rejected_changes": [],
        },
    )
    _write_yaml(
        turn1 / "events.yaml",
        [
            {
                "id": "event_0001",
                "turn": 1,
                "type": "thread_update",
                "text": "a new thread",
                "visibility": "gm_only",
                "effects": {"action": "open", "thread_id": "thread_001"},
            },
            {
                "id": "event_0002",
                "turn": 1,
                "type": "threat_pressure",
                "text": "pressure rises",
                "visibility": "gm_only",
                "effects": {"threat_id": "threat_001", "pressure": 30, "roll_id": "roll_0001"},
            },
            {
                "id": "event_0101",
                "turn": 1,
                "type": "combat",
                "cause": "character:char_001:0",
                "effects": {"combat": {}},
            },
            {
                "id": "event_0102",
                "turn": 1,
                "type": "encounter",
                "effects": {"encounter_id": "encounter_001"},
            },
            {
                "id": "event_0103",
                "turn": 1,
                "type": "dice_roll_request",
                "effects": {"roll_id": "roll_0101"},
            },
        ],
    )
    _write_yaml(
        turn1 / "rolls.yaml",
        [
            {"id": "roll_0001", "turn": 1, "type": "dice", "result": 30},
            {"id": "roll_0101", "turn": 1, "type": "chance", "outcome": "success"},
        ],
    )
    _write_yaml(
        turn1 / "intervention.yaml",
        {
            "interventions": [
                {
                    "type": "character_directive",
                    "user_role": "player_character",
                    "target": {"kind": "character", "id": "char_001"},
                    "content": "出口へ進む",
                }
            ]
        },
    )
    _write_yaml(
        turn1 / "agent_io" / "act_candidates.yaml",
        [
            {
                "character_id": "char_001",
                "action_text": "出口へ進む",
                "source_index": 0,
            }
        ],
    )
    _write_yaml(turn1 / "checks.yaml", {"findings": [{"severity": "warn", "source": "leak"}]})

    # Turn 2: emotion +40 (70 -> 100, at ceiling), a thread advances, threat_001 crosses its
    # only stage, and the story's single scene transition (2 diff changes: end + start).
    turn2 = runs_dir / "turn_0002"
    _write_yaml(turn2 / "meta.yaml", {"turn": 2, "status": "applied"})
    _write_yaml(
        turn2 / "state_diff.yaml",
        {
            "diff": {
                "id": "diff_0002",
                "turn": 2,
                "changes": [
                    {
                        "target": "character",
                        "op": "delta",
                        "path": "emotions.fear",
                        "value": 40,
                        "id": "char_001",
                        "visibility": "character",
                    },
                    {
                        "target": "scene",
                        "op": "set",
                        "path": "status",
                        "value": "ended",
                        "id": "scene_001",
                        "visibility": "scene",
                    },
                    {
                        "target": "quests",
                        "id": "quest_001",
                        "op": "set",
                        "path": "status",
                        "value": "advanced",
                        "visibility": "reader",
                    },
                    {
                        "target": "scene",
                        "op": "set",
                        "path": "status",
                        "value": "active",
                        "id": "scene_002",
                        "visibility": "scene",
                    },
                ],
            },
            "applied": True,
            "rejected_changes": [],
        },
    )
    _write_yaml(
        turn2 / "events.yaml",
        [
            {
                "id": "event_0003",
                "turn": 2,
                "type": "thread_update",
                "text": "the thread advances",
                "visibility": "gm_only",
                "effects": {"action": "advance", "thread_id": "thread_001"},
            },
            {
                "id": "event_0004",
                "turn": 2,
                "type": "threat_pressure",
                "text": "pressure rises",
                "visibility": "gm_only",
                "effects": {"threat_id": "threat_001", "pressure": 55, "roll_id": "roll_0002"},
            },
            {
                "id": "event_0005",
                "turn": 2,
                "type": "threat_stage",
                "text": "stage fired",
                "visibility": "gm_only",
                "effects": {"threat_id": "threat_001", "stage_at": 50, "roll_id": "roll_0002"},
            },
            {
                "id": "event_0006",
                "turn": 2,
                "type": "pacing_stall",
                "text": "stalled",
                "visibility": "gm_only",
                "effects": {"stalled_turns": 3},
            },
        ],
    )
    _write_yaml(
        turn2 / "rolls.yaml", [{"id": "roll_0002", "turn": 2, "type": "dice", "result": 25}]
    )
    _write_yaml(
        turn2 / "checks.yaml",
        {
            "findings": [
                {"severity": "error", "source": "continuity"},
                {"severity": "warn", "source": "leak"},
            ]
        },
    )

    # Turn 3: emotion +10 (100 + 10 clamps back to 100, ceiling continues), thread resolves,
    # narrative still stalled (consecutive with turn 2). No checker findings this turn.
    turn3 = runs_dir / "turn_0003"
    _write_yaml(turn3 / "meta.yaml", {"turn": 3, "status": "applied"})
    _write_yaml(
        turn3 / "state_diff.yaml",
        {
            "diff": {
                "id": "diff_0003",
                "turn": 3,
                "changes": [
                    {
                        "target": "character",
                        "op": "delta",
                        "path": "emotions.fear",
                        "value": 10,
                        "id": "char_001",
                        "visibility": "character",
                    },
                    {
                        "target": "quests",
                        "id": "quest_001",
                        "op": "set",
                        "path": "status",
                        "value": "resolved",
                        "visibility": "reader",
                    },
                ],
            },
            "applied": True,
            "rejected_changes": [],
        },
    )
    _write_yaml(
        turn3 / "events.yaml",
        [
            {
                "id": "event_0007",
                "turn": 3,
                "type": "thread_update",
                "text": "the thread resolves",
                "visibility": "gm_only",
                "effects": {"action": "resolve", "thread_id": "thread_001"},
            },
            {
                "id": "event_0008",
                "turn": 3,
                "type": "pacing_stall",
                "text": "still stalled",
                "visibility": "gm_only",
                "effects": {"stalled_turns": 4},
            },
        ],
    )
    _write_yaml(turn3 / "checks.yaml", {"findings": []})

    # A discarded retry of turn 2 and a rolled-back turn 3 (D112 naming): excluded from
    # `existing_turn_numbers`/live-turn history, only counted in `turns.discarded/rolledback`.
    _write_yaml(runs_dir / "turn_0002_discarded_1" / "meta.yaml", {"turn": 2, "status": "failed"})
    _write_yaml(runs_dir / "turn_0003_rolledback_1" / "meta.yaml", {"turn": 3, "status": "applied"})

    return project_path


def test_collect_metrics_hand_computed(tmp_path):
    project_path = _build_hand_fixture(tmp_path)

    result = collect_metrics(project_path)

    assert result.turns.total == 3
    assert result.turns.timeline_entries == 3
    assert result.turns.by_status == {"applied": 3}
    assert result.turns.discarded == 1
    assert result.turns.rolledback == 1

    (character,) = result.emotions
    assert character.character_id == "char_001"
    by_emotion = {e.emotion: e for e in character.emotions}
    fear = by_emotion["fear"]
    assert fear.final == 100
    assert fear.min == 20  # baseline is part of the reconstructed trajectory
    assert fear.max == 100
    assert fear.max_consecutive_at_ceiling == 2  # turns 2 and 3
    calm = by_emotion["calm"]
    assert calm.final == 50
    assert calm.min is None
    assert calm.max is None
    assert calm.max_consecutive_at_ceiling is None

    assert result.pacing.stall_event_count == 2
    assert result.pacing.max_consecutive_stall_turns == 2

    assert result.threads.opened == 1
    assert result.threads.advanced == 1
    assert result.threads.resolved == 1
    assert result.threads.max_open_turns == 2  # thread_001: opened turn 1, last turn 3
    assert result.threads.resolved_ratio == 1.0

    (threat,) = result.threats
    assert threat.threat_id == "threat_001"
    assert threat.initial_pressure == 0  # turn 1's pressure(30) - roll result(30)
    assert threat.final_pressure == 55
    assert threat.stage_fired_turns == {"50": 2}

    assert result.scenes.transition_count == 1  # one transition == 2 status-set diffs
    assert result.scenes.final_active_count == 1
    assert result.scenes.final_active_scene_ids == ["scene_002"]
    assert result.scenes.final_statuses == {"scene_001": "ended", "scene_002": "active"}

    assert result.checks.by_source == {"leak": 2, "continuity": 1}
    assert result.checks.by_severity == {"warn": 2, "error": 1}
    assert result.checks.leak_by_severity == {"warn": 2}

    assert result.memory.summary_count == 2
    assert result.game.combat_count == 1
    assert result.game.quest_opened == 1
    assert result.game.quest_advanced == 1
    assert result.game.quest_resolved == 1
    assert result.game.applied_pc_action_count == 1
    assert result.game.encounter_count == 1
    assert result.game.skill_check_successes == 1
    assert result.game.skill_check_total == 1
    assert result.game.skill_check_success_rate == 1.0
    assert result.replay.match_rate is None  # pre-066 hand-written fixture has no RNG pins


def test_collect_metrics_on_a_project_with_zero_turns(tmp_path):
    project_path = create_project(tmp_path / "proj", title="empty", template="minimal")

    result = collect_metrics(project_path)

    assert result.turns.total == 0
    assert result.turns.timeline_entries == 0
    assert result.turns.by_status == {}
    assert result.turns.discarded == 0
    assert result.turns.rolledback == 0
    assert result.emotions == []
    assert result.pacing.stall_event_count == 0
    assert result.pacing.max_consecutive_stall_turns == 0
    assert result.threads == result.threads.__class__(
        opened=0, advanced=0, resolved=0, max_open_turns=None, resolved_ratio=None
    )
    assert result.threats == []
    assert result.scenes.transition_count == 0
    assert result.scenes.final_active_count == 0
    assert result.checks.by_source == {}
    assert result.checks.by_severity == {}
    assert result.checks.leak_by_severity == {}
    assert result.memory.summary_count == 0
    assert result.game.skill_check_success_rate is None
    assert result.replay.match_rate is None


def test_replay_match_rate_uses_pinned_rng_offsets(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    for turn, offset, draws in ((1, 0, 2), (2, 2, 1), (3, 3, 4)):
        _write_yaml(
            runs_dir / f"turn_{turn:04d}" / "meta.yaml",
            {
                "turn": turn,
                "status": "applied",
                "rng_start_offset": offset,
                "rng_draws_consumed": draws,
            },
        )

    replay = collect_metrics(project_path).replay

    assert replay.matched_turns == 3
    assert replay.evaluated_turns == 3
    assert replay.match_rate == 1.0

    _write_yaml(
        runs_dir / "turn_0003" / "meta.yaml",
        {"turn": 3, "status": "applied", "rng_start_offset": 99, "rng_draws_consumed": 4},
    )
    assert collect_metrics(project_path).replay.match_rate == 2 / 3


def test_game_metrics_exclude_reject_all_turn(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    turn1 = project_path.parent / "workspace" / "runs" / "turn_0001"
    _write_yaml(turn1 / "review.yaml", {"decision": "reject_all"})

    game = collect_metrics(project_path).game

    assert game.combat_count == 0
    assert game.quest_opened == 0
    assert game.applied_pc_action_count == 0
    assert game.encounter_count == 0
    assert game.skill_check_total == 0


def test_pc_action_metric_excludes_candidate_that_loses_exclusive_resolution(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    turn1 = project_path.parent / "workspace" / "runs" / "turn_0001"
    events = yaml.safe_load((turn1 / "events.yaml").read_text(encoding="utf-8"))
    for event in events:
        if event.get("cause") == "character:char_001:0":
            event["cause"] = "character:char_002:0"
    _write_yaml(turn1 / "events.yaml", events)

    assert collect_metrics(project_path).game.applied_pc_action_count == 0


def test_pc_action_metric_does_not_double_count_duplicate_directives(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    turn1 = project_path.parent / "workspace" / "runs" / "turn_0001"
    intervention_path = turn1 / "intervention.yaml"
    intervention = yaml.safe_load(intervention_path.read_text(encoding="utf-8"))
    intervention["interventions"].append(dict(intervention["interventions"][0]))
    _write_yaml(intervention_path, intervention)

    assert collect_metrics(project_path).game.applied_pc_action_count == 1


def test_pc_action_metric_excludes_rejected_resolve_event(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    turn1 = project_path.parent / "workspace" / "runs" / "turn_0001"
    events = yaml.safe_load((turn1 / "events.yaml").read_text(encoding="utf-8"))
    for event in events:
        if event.get("cause") == "character:char_001:0":
            event["type"] = "combat_rejected"
    _write_yaml(turn1 / "events.yaml", events)

    assert collect_metrics(project_path).game.applied_pc_action_count == 0


def test_game_metrics_require_applied_meta_status(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    turn1 = project_path.parent / "workspace" / "runs" / "turn_0001"
    _write_yaml(turn1 / "meta.yaml", {"turn": 1, "status": "stopped_for_review"})

    game = collect_metrics(project_path).game

    assert game.combat_count == 0
    assert game.quest_opened == 0
    assert game.applied_pc_action_count == 0


def test_collect_metrics_raises_for_invalid_project(tmp_path):
    missing = tmp_path / "does_not_exist" / "project.yaml"
    try:
        collect_metrics(missing)
        raise AssertionError("expected MetricsError")
    except MetricsError:
        pass
