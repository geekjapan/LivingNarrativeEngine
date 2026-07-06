"""Issue 011: pacing/stall checker -- warns but never blocks auto-apply."""

from pathlib import Path

from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.pacing_check import pacing_checker
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import (
    Event,
    PacingConfig,
    Visibility,
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


def _context(tmp_path: Path, turn: int, *, stall_window: int = 3) -> TurnContext:
    world = WorldState(
        id="world_001",
        name="World",
        summary="",
        pacing=PacingConfig(stall_window=stall_window, pressure_boost=4),
    )
    return TurnContext(
        turn=turn,
        project=None,
        paths=_paths(tmp_path),
        bundle=WorldStateBundle(world=world),
        random_engine=None,
    )


def _event(event_type: str, **effects) -> Event:
    return Event(
        id="event_0001",
        turn=1,
        type=event_type,
        text="x",
        visibility=Visibility.GM_ONLY,
        effects=effects,
    )


def test_warns_when_stalled_and_no_current_turn_advancement(tmp_path):
    context = _context(tmp_path, turn=4, stall_window=3)

    findings = pacing_checker(context, "", [], StateDiff(id="diff_0004", turn=4))

    assert len(findings) == 1
    assert findings[0].checker == "pacing_check"
    assert findings[0].severity == "warn"
    assert "3" in findings[0].message


def test_silent_when_current_turn_has_a_threat_stage(tmp_path):
    context = _context(tmp_path, turn=4, stall_window=3)

    findings = pacing_checker(
        context, "", [_event("threat_stage")], StateDiff(id="diff_0004", turn=4)
    )

    assert findings == []


def test_silent_when_current_turn_has_a_scene_transition(tmp_path):
    context = _context(tmp_path, turn=4, stall_window=3)

    findings = pacing_checker(
        context,
        "",
        [_event("narrative", scene_transition={"end": "scene_001", "start": "scene_002"})],
        StateDiff(id="diff_0004", turn=4),
    )

    assert findings == []


def test_silent_when_not_stalled(tmp_path):
    # window off (default 0).
    context = _context(tmp_path, turn=4, stall_window=0)

    findings = pacing_checker(context, "", [], StateDiff(id="diff_0004", turn=4))

    assert findings == []


def test_silent_when_too_early_to_judge(tmp_path):
    context = _context(tmp_path, turn=3, stall_window=3)

    findings = pacing_checker(context, "", [], StateDiff(id="diff_0003", turn=3))

    assert findings == []
