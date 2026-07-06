from pathlib import Path

import yaml

from living_narrative.agents.event_history import load_recent_events
from living_narrative.state.models import TimelineEntry


def _write_events(turn_dir: Path, events: list[dict]) -> None:
    turn_dir.mkdir(parents=True, exist_ok=True)
    (turn_dir / "events.yaml").write_text(
        yaml.safe_dump(events, allow_unicode=True), encoding="utf-8"
    )


def _event(event_id: str, turn: int, text: str) -> dict:
    return {
        "id": event_id,
        "turn": turn,
        "type": "narrative",
        "text": text,
        "visibility": "reader",
    }


def test_load_recent_events_reads_multi_turn_artifacts_in_order(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_events(runs_dir / "turn_0001", [_event("event_0001", 1, "turn one event")])
    _write_events(runs_dir / "turn_0002", [_event("event_0002", 2, "turn two event")])
    timeline = [
        TimelineEntry(turn=1, event_ids=["event_0001"]),
        TimelineEntry(turn=2, event_ids=["event_0002"]),
    ]

    events = load_recent_events(runs_dir, timeline, max_turns=2)

    assert [event.id for event in events] == ["event_0001", "event_0002"]
    assert [event.text for event in events] == ["turn one event", "turn two event"]


def test_load_recent_events_respects_max_turns(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_events(runs_dir / "turn_0001", [_event("event_0001", 1, "turn one event")])
    _write_events(runs_dir / "turn_0002", [_event("event_0002", 2, "turn two event")])
    _write_events(runs_dir / "turn_0003", [_event("event_0003", 3, "turn three event")])
    timeline = [
        TimelineEntry(turn=1, event_ids=["event_0001"]),
        TimelineEntry(turn=2, event_ids=["event_0002"]),
        TimelineEntry(turn=3, event_ids=["event_0003"]),
    ]

    events = load_recent_events(runs_dir, timeline, max_turns=2)

    assert [event.id for event in events] == ["event_0002", "event_0003"]


def test_load_recent_events_skips_missing_artifact(tmp_path):
    runs_dir = tmp_path / "runs"
    # turn_0001 has no artifact at all (e.g. evicted/never written).
    _write_events(runs_dir / "turn_0002", [_event("event_0002", 2, "turn two event")])
    timeline = [
        TimelineEntry(turn=1, event_ids=["event_0001"]),
        TimelineEntry(turn=2, event_ids=["event_0002"]),
    ]

    events = load_recent_events(runs_dir, timeline, max_turns=2)

    assert [event.id for event in events] == ["event_0002"]


def test_load_recent_events_skips_missing_event_id_within_artifact(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_events(runs_dir / "turn_0001", [_event("event_0001", 1, "kept event")])
    timeline = [TimelineEntry(turn=1, event_ids=["event_0001", "event_9999"])]

    events = load_recent_events(runs_dir, timeline, max_turns=1)

    assert [event.id for event in events] == ["event_0001"]


def test_load_recent_events_returns_empty_for_empty_timeline(tmp_path):
    assert load_recent_events(tmp_path / "runs", [], max_turns=3) == []


def test_load_recent_events_returns_empty_for_zero_max_turns(tmp_path):
    timeline = [TimelineEntry(turn=1, event_ids=["event_0001"])]

    assert load_recent_events(tmp_path / "runs", timeline, max_turns=0) == []
