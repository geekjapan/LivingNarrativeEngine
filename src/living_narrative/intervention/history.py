"""Project-wide Intervention history index (spec.md Requirement "Intervention履歴インデックス").

Written to ``workspace/interventions.yaml``, appended-to once per turn at Commit completion
(never rewritten in place — matches the diff/roll/event no-overwrite convention).
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event


class InterventionHistoryEntry(BaseModel):
    id: str
    turn: int
    type: str
    source_event_ids: list[str] = Field(default_factory=list)
    diff_id: str | None = None
    superseded_by_rerun: bool = False


class InterventionHistory(BaseModel):
    entries: list[InterventionHistoryEntry] = Field(default_factory=list)


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


def load_history(path: Path) -> InterventionHistory:
    if not path.exists():
        return InterventionHistory()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return InterventionHistory.model_validate(data)


def build_history_entries(
    interventions: list[dict[str, Any]],
    resolved_events: list[Event],
    diff: StateDiff,
) -> list[InterventionHistoryEntry]:
    """One entry per intervention, tracing to whatever this turn actually did (or didn't do)."""
    entries = []
    for item in interventions:
        cause_tag = f"intervention:{item['id']}"
        source_event_ids = [event.id for event in resolved_events if event.cause == cause_tag]
        has_diff_change = any(change.source_event in source_event_ids for change in diff.changes)
        entries.append(
            InterventionHistoryEntry(
                id=item["id"],
                turn=item["turn"],
                type=item["type"],
                source_event_ids=source_event_ids,
                diff_id=diff.id if has_diff_change else None,
            )
        )
    return entries


def append_history(path: Path, new_entries: list[InterventionHistoryEntry]) -> None:
    if not new_entries:
        return
    history = load_history(path)
    history.entries.extend(new_entries)
    _atomic_write_yaml(path, history.model_dump(mode="json"))


def mark_superseded_by_rerun(path: Path, event_ids: set[str]) -> None:
    """Flip ``superseded_by_rerun`` on entries whose source events came from a discarded attempt.

    Content otherwise stays untouched (no-overwrite principle, D112) — used by the future
    ``rerun_turn`` operation (session-autonomy); not exercised by this change's own pipeline.
    """
    history = load_history(path)
    if not history.entries:
        return
    changed = False
    for entry in history.entries:
        if not entry.superseded_by_rerun and set(entry.source_event_ids) & event_ids:
            entry.superseded_by_rerun = True
            changed = True
    if changed:
        _atomic_write_yaml(path, history.model_dump(mode="json"))
