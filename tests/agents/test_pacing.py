"""Issue 011: shared narrative-stall detection."""

from pathlib import Path

import yaml

from living_narrative.agents.pacing import detect_stall
from living_narrative.pipeline.context import TurnContext
from living_narrative.state.models import (
    CanonEntry,
    PacingConfig,
    ReaderStateEntry,
    TimelineEntry,
    WorldState,
    WorldStateBundle,
)
from living_narrative.workspace.loader import WorkspacePaths


def _paths(tmp_path: Path) -> WorkspacePaths:
    return WorkspacePaths(
        root=tmp_path,
        state=tmp_path / "state",
        runs=tmp_path / "runs",
        exports=tmp_path / "exports",
    )


def _write_events(runs_dir: Path, turn: int, events: list[dict]) -> None:
    turn_dir = runs_dir / f"turn_{turn:04d}"
    turn_dir.mkdir(parents=True, exist_ok=True)
    (turn_dir / "events.yaml").write_text(
        yaml.safe_dump(events, allow_unicode=True), encoding="utf-8"
    )


def _event(event_id: str, turn: int, event_type: str, **effects) -> dict:
    return {
        "id": event_id,
        "turn": turn,
        "type": event_type,
        "text": "x",
        "visibility": "gm_only",
        "effects": effects,
    }


def _context(
    tmp_path: Path,
    turn: int,
    *,
    stall_window: int = 3,
    timeline: list[TimelineEntry] | None = None,
    reader_state: list[ReaderStateEntry] | None = None,
    canon: list[CanonEntry] | None = None,
) -> TurnContext:
    world = WorldState(
        id="world_001",
        name="World",
        summary="",
        pacing=PacingConfig(stall_window=stall_window, pressure_boost=4),
    )
    bundle = WorldStateBundle(
        world=world,
        timeline=timeline or [],
        reader_state=reader_state or [],
        canon=canon or [],
    )
    return TurnContext(
        turn=turn, project=None, paths=_paths(tmp_path), bundle=bundle, random_engine=None
    )


def test_detect_stall_is_off_by_default(tmp_path):
    context = _context(tmp_path, turn=10, stall_window=0)

    assert detect_stall(context) is None


def test_detect_stall_returns_none_when_turn_is_too_early(tmp_path):
    # window covers turns 1..2; there's no prior turn to have judged them by turn 3.
    context = _context(tmp_path, turn=3, stall_window=3)

    assert detect_stall(context) is None


def test_detect_stall_detects_stall_with_no_advancement_signal(tmp_path):
    context = _context(tmp_path, turn=4, stall_window=3)

    assert detect_stall(context) == 3


def test_threat_pressure_and_background_event_do_not_count_as_advancement(tmp_path):
    _write_events(
        tmp_path / "runs",
        3,
        [
            _event("event_0001", 3, "threat_pressure"),
            _event("event_0002", 3, "background_event"),
        ],
    )
    timeline = [TimelineEntry(turn=3, event_ids=["event_0001", "event_0002"])]
    context = _context(tmp_path, turn=4, stall_window=3, timeline=timeline)

    assert detect_stall(context) == 3


def test_threat_stage_event_resets_stall_detection(tmp_path):
    _write_events(tmp_path / "runs", 2, [_event("event_0001", 2, "threat_stage")])
    timeline = [TimelineEntry(turn=2, event_ids=["event_0001"])]
    context = _context(tmp_path, turn=4, stall_window=3, timeline=timeline)

    assert detect_stall(context) is None


def test_scene_end_event_resets_stall_detection(tmp_path):
    _write_events(tmp_path / "runs", 2, [_event("event_0001", 2, "scene_end")])
    timeline = [TimelineEntry(turn=2, event_ids=["event_0001"])]
    context = _context(tmp_path, turn=4, stall_window=3, timeline=timeline)

    assert detect_stall(context) is None


def test_scene_transition_effect_resets_stall_detection(tmp_path):
    _write_events(
        tmp_path / "runs",
        2,
        [
            _event(
                "event_0001",
                2,
                "narrative",
                scene_transition={"end": "scene_001", "start": "scene_002"},
            )
        ],
    )
    timeline = [TimelineEntry(turn=2, event_ids=["event_0001"])]
    context = _context(tmp_path, turn=4, stall_window=3, timeline=timeline)

    assert detect_stall(context) is None


def test_new_reader_state_entry_resets_stall_detection(tmp_path):
    reader_state = [
        ReaderStateEntry(id="reader_state_0001", text="x", established_turn=2, disclosed_turn=2)
    ]
    context = _context(tmp_path, turn=4, stall_window=3, reader_state=reader_state)

    assert detect_stall(context) is None


def test_new_canon_entry_resets_stall_detection(tmp_path):
    canon = [CanonEntry(id="canon_0001", text="x", established_turn=2)]
    context = _context(tmp_path, turn=4, stall_window=3, canon=canon)

    assert detect_stall(context) is None


def test_reader_state_entry_outside_the_window_does_not_reset(tmp_path):
    # window (turn=5, stall_window=3) covers turns 2..4; established_turn=1 is out of range.
    reader_state = [
        ReaderStateEntry(id="reader_state_0001", text="x", established_turn=1, disclosed_turn=1)
    ]
    context = _context(tmp_path, turn=5, stall_window=3, reader_state=reader_state)

    assert detect_stall(context) == 3
