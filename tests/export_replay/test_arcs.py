"""Unit tests for ``export_replay.arcs.build_arcs_report`` (docs/issues/028-029).

Turn artifacts are hand-written directly (same approach as ``tests/session/test_metrics.py``)
so every number in ``ArcsReport`` can be hand-computed and asserted exactly.
"""

from pathlib import Path

import yaml

from living_narrative.export_replay.arcs import ArcsError, build_arcs_report, render_arcs_markdown
from living_narrative.workspace.init import create_project


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _build_hand_fixture(tmp_path: Path) -> Path:
    project_path = create_project(tmp_path / "proj", title="arcs fixture", template="minimal")
    state_dir = project_path.parent / "workspace" / "state"

    _write_yaml(
        state_dir / "world.yaml",
        {"id": "world_001", "name": "Test World", "summary": "A quiet test world."},
    )
    _write_yaml(state_dir / "canon.yaml", [])
    _write_yaml(state_dir / "reader_state.yaml", [])
    _write_yaml(state_dir / "gm_vault.yaml", [])
    _write_yaml(state_dir / "factions.yaml", [])
    _write_yaml(state_dir / "timeline.yaml", [])
    _write_yaml(
        state_dir / "relationships.yaml",
        [
            {
                "from": "char_001",
                "to": "char_002",
                # trust: hand-computable trajectory (no clamping ever fires).
                # tension: deliberately clamp-ambiguous (see test assertions below).
                "trust": 70,
                "affection": 50,
                "tension": 50,
                "suspicion": 10,
            }
        ],
    )
    _write_yaml(
        state_dir / "unresolved_threads.yaml",
        [
            {
                "id": "thread_001",
                "description": "open, never resolved",
                "status": "open",
                "opened_turn": 1,
            },
            {
                "id": "thread_002",
                "description": "resolved via thread_update event",
                "status": "resolved",
                "opened_turn": 2,
            },
            {
                "id": "thread_003",
                "description": "resolved with no turn evidence (e.g. manual edit)",
                "status": "resolved",
                "opened_turn": 1,
            },
        ],
    )
    _write_yaml(
        state_dir / "memory_summaries.yaml",
        [
            {"id": "memory_0002", "up_to_turn": 2, "text": "and then..."},
            {"id": "memory_0001", "up_to_turn": 1, "text": "so far..."},
        ],
    )
    _write_yaml(
        state_dir / "characters" / "char_001.yaml",
        {
            "id": "char_001",
            "name": "Aoi",
            "role": "detective",
            "emotions": {"fear": 100, "calm": 50},
            "emotions_baseline": {"fear": 20},
        },
    )
    _write_yaml(
        state_dir / "characters" / "char_002.yaml",
        {"id": "char_002", "name": "Ren", "role": "witness"},
    )
    _write_yaml(
        state_dir / "scenes" / "scene_001.yaml",
        {"id": "scene_001", "location": "station", "time": "night", "status": "active"},
    )

    runs_dir = project_path.parent / "workspace" / "runs"

    def _relationship_change(path, value):
        return {
            "target": "relationship",
            "op": "delta",
            "path": path,
            "value": value,
            "id": "char_001__char_002",
            "visibility": "gm_only",
        }

    def _emotion_change(value):
        return {
            "target": "character",
            "op": "delta",
            "path": "emotions.fear",
            "value": value,
            "id": "char_001",
            "visibility": "character",
        }

    # Turn 1: fear 20 -> 70; trust +10; tension +120 (deliberately over-range: clamp-ambiguous);
    # thread_001 opens.
    turn1 = runs_dir / "turn_0001"
    _write_yaml(turn1 / "meta.yaml", {"turn": 1, "status": "applied"})
    _write_yaml(
        turn1 / "state_diff.yaml",
        {
            "diff": {
                "id": "diff_0001",
                "turn": 1,
                "changes": [
                    _emotion_change(50),
                    _relationship_change("trust", 10),
                    _relationship_change("tension", 120),
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
            }
        ],
    )

    # Turn 2: fear 70 -> 100 (ceiling); trust +15; tension -70; thread_001 advances,
    # thread_002 opens (no test coverage needed) then resolves in turn 3.
    turn2 = runs_dir / "turn_0002"
    _write_yaml(turn2 / "meta.yaml", {"turn": 2, "status": "applied"})
    _write_yaml(
        turn2 / "state_diff.yaml",
        {
            "diff": {
                "id": "diff_0002",
                "turn": 2,
                "changes": [
                    _emotion_change(40),
                    _relationship_change("trust", 15),
                    _relationship_change("tension", -70),
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
                "id": "event_0002",
                "turn": 2,
                "type": "thread_update",
                "text": "the thread advances",
                "visibility": "gm_only",
                "effects": {"action": "advance", "thread_id": "thread_001"},
            }
        ],
    )

    # Turn 3: fear +10 (100 clamped, no change); trust -5 (65 -> ... -> 70); thread_002 resolves.
    turn3 = runs_dir / "turn_0003"
    _write_yaml(turn3 / "meta.yaml", {"turn": 3, "status": "applied"})
    _write_yaml(
        turn3 / "state_diff.yaml",
        {
            "diff": {
                "id": "diff_0003",
                "turn": 3,
                "changes": [
                    _emotion_change(10),
                    _relationship_change("trust", -5),
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
                "id": "event_0003",
                "turn": 3,
                "type": "thread_update",
                "text": "thread_002 resolves",
                "visibility": "gm_only",
                "effects": {"action": "resolve", "thread_id": "thread_002"},
            }
        ],
    )

    return project_path


def test_build_arcs_report_hand_computed(tmp_path):
    project_path = _build_hand_fixture(tmp_path)

    report = build_arcs_report(project_path)

    by_character = {c.character_id: c for c in report.emotions}
    character = by_character["char_001"]
    # fear: 20->70 (turn1), 70->100 (turn2); turn3's +10 clamps 100->100 (no reported change).
    assert [(c.turn, c.emotion, c.before, c.after) for c in character.changes] == [
        (1, "fear", 20, 70),
        (2, "fear", 70, 100),
    ]
    assert by_character["char_002"].changes == []  # no emotions at all

    by_dimension: dict[str, list] = {}
    for change in report.relationships:
        by_dimension.setdefault(change.dimension, []).append(change)

    trust = by_dimension["trust"]
    # final trust=70, deltas [10, 15, -5] sum to 20 -> candidate initial 50, and replaying
    # forward never clamps, so every resulting value is exactly reconstructable.
    assert [(c.turn, c.delta, c.resulting_value) for c in trust] == [
        (1, 10, 60),
        (2, 15, 75),
        (3, -5, 70),
    ]
    for c in trust:
        assert c.from_id == "char_001"
        assert c.to_id == "char_002"

    tension = by_dimension["tension"]
    # final tension=50, deltas [120, -70] sum to 50 -> candidate initial 0, but replaying
    # forward from 0 clamps at +120 (-> 100 rather than 120), so the reconstruction can't
    # reproduce the true history: every entry in this group is reported unknown.
    assert [(c.turn, c.delta, c.resulting_value) for c in tension] == [
        (1, 120, None),
        (2, -70, None),
    ]

    threads_by_id = {t.id: t for t in report.threads}
    thread_001 = threads_by_id["thread_001"]
    assert thread_001.opened_turn == 1
    assert thread_001.advances == 1
    assert thread_001.resolved_turn is None
    assert thread_001.stalled_turns == 2  # last turn (3) - opened_turn (1)

    thread_002 = threads_by_id["thread_002"]
    assert thread_002.opened_turn == 2
    assert thread_002.advances == 0
    assert thread_002.resolved_turn == 3
    assert thread_002.stalled_turns is None

    thread_003 = threads_by_id["thread_003"]
    assert thread_003.resolved_turn is None  # resolved with no thread_update event evidence
    assert thread_003.stalled_turns is None  # already resolved -> never counted as stalled

    assert [m.id for m in report.memory_summaries] == ["memory_0001", "memory_0002"]  # sorted


def test_build_arcs_report_on_a_project_with_zero_turns(tmp_path):
    project_path = create_project(tmp_path / "proj", title="empty", template="minimal")

    report = build_arcs_report(project_path)

    assert report.emotions == []
    assert report.relationships == []
    assert report.threads == []
    assert report.memory_summaries == []


def test_build_arcs_report_raises_for_invalid_project(tmp_path):
    missing = tmp_path / "does_not_exist" / "project.yaml"
    try:
        build_arcs_report(missing)
        raise AssertionError("expected ArcsError")
    except ArcsError:
        pass


def test_render_arcs_markdown_includes_all_sections(tmp_path):
    project_path = _build_hand_fixture(tmp_path)
    report = build_arcs_report(project_path)

    content = render_arcs_markdown(report)

    assert "# キャラクターアーク・伏線レポート" in content
    assert "## 感情推移" in content
    assert "## 関係推移" in content
    assert "## スレッド" in content
    assert "## メモリ要約" in content
    assert "fear 20→70" in content
    assert "不明" in content  # the clamp-ambiguous tension entries
    assert "so far..." in content
