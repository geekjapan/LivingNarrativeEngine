"""Load past-turn events for Character Agent context (Issue 006).

Reads ``timeline.yaml``'s entries (turn -> event_ids) and re-hydrates the
matching ``Event`` bodies from each turn's ``events.yaml`` artifact.
"""

from pathlib import Path

import yaml

from living_narrative.pipeline.turn_numbering import turn_dir_path
from living_narrative.state.models import Event, TimelineEntry


def load_recent_events(
    runs_dir: Path, timeline: list[TimelineEntry], max_turns: int
) -> list[Event]:
    """Ordered ``Event`` bodies for the last ``max_turns`` timeline entries.

    Fail-soft: a turn whose ``events.yaml`` artifact is missing (or an
    event id absent from it) is skipped rather than raising, since turn
    artifacts are best-effort history, not a required dependency.
    """
    if max_turns <= 0 or not timeline:
        return []

    events: list[Event] = []
    for entry in timeline[-max_turns:]:
        events_path = turn_dir_path(runs_dir, entry.turn) / "events.yaml"
        if not events_path.exists():
            continue
        raw_events = yaml.safe_load(events_path.read_text(encoding="utf-8")) or []
        by_id = {item.get("id"): item for item in raw_events}
        for event_id in entry.event_ids:
            data = by_id.get(event_id)
            if data is None:
                continue
            events.append(Event.model_validate(data))
    return events
