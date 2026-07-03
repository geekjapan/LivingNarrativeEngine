"""Project-wide sequential ``event_NNNN`` id allocation (spec-foundation.md §3)."""

import re
from collections.abc import Callable
from pathlib import Path

import yaml

_EVENT_ID_RE = re.compile(r"^event_(\d+)$")


def _max_event_number(runs_dir: Path) -> int:
    max_number = 0
    if not runs_dir.exists():
        return 0
    for entry in runs_dir.iterdir():
        events_path = entry / "events.yaml"
        if not entry.is_dir() or not events_path.exists():
            continue
        items = yaml.safe_load(events_path.read_text(encoding="utf-8")) or []
        for item in items:
            match = _EVENT_ID_RE.match(str(item.get("id", "")))
            if match:
                max_number = max(max_number, int(match.group(1)))
    return max_number


def make_event_id_allocator(runs_dir: Path) -> Callable[[], str]:
    """Return a callable that hands out fresh, project-wide-unique ``event_NNNN`` ids."""
    counter = _max_event_number(runs_dir)

    def allocate() -> str:
        nonlocal counter
        counter += 1
        return f"event_{counter:04d}"

    return allocate
