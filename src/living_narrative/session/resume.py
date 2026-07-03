"""Workspace-only session resume reconstruction."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from living_narrative.pipeline.rng_state import total_rng_draws_consumed
from living_narrative.pipeline.status import UNRESOLVED_STATUSES, TurnStatus
from living_narrative.pipeline.turn_numbering import ANY_TURN_DIR_RE, read_turn_status

_LIVE_TURN_RE = re.compile(r"^turn_(\d+)$")
_ID_RE = re.compile(r"\b(event|diff|roll|int)_(\d{4,})\b")


@dataclass(frozen=True)
class ResumeState:
    last_applied_turn: int | None
    pending_review_turn: int | None
    rng_draws_consumed: int
    next_ids: dict[str, str]

    @property
    def should_present_pending_review_first(self) -> bool:
        return self.pending_review_turn is not None


def _turn_number(path: Path) -> int:
    match = re.match(r"^turn_(\d+)", path.name)
    return int(match.group(1)) if match else 0


def _turn_dirs(runs_dir: Path) -> list[Path]:
    if not runs_dir.exists():
        return []
    entries = [
        entry
        for entry in runs_dir.iterdir()
        if entry.is_dir() and ANY_TURN_DIR_RE.match(entry.name)
    ]
    return sorted(entries, key=lambda path: path.name)


def _scan_ids(data: Any, maximums: dict[str, int]) -> None:
    if isinstance(data, dict):
        for value in data.values():
            _scan_ids(value, maximums)
    elif isinstance(data, list):
        for value in data:
            _scan_ids(value, maximums)
    elif isinstance(data, str):
        for kind, number in _ID_RE.findall(data):
            maximums[kind] = max(maximums[kind], int(number))


def _scan_yaml(path: Path, maximums: dict[str, int]) -> None:
    if not path.exists():
        return
    _scan_ids(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, maximums)


def restore_next_id_counters(runs_dir: Path, interventions_path: Path) -> dict[str, str]:
    maximums = {"event": 0, "diff": 0, "roll": 0, "int": 0}
    for turn_dir in _turn_dirs(runs_dir):
        for name in (
            "events.yaml",
            "state_diff.yaml",
            "state_diff_pre_review.yaml",
            "rolls.yaml",
            "intervention.yaml",
        ):
            _scan_yaml(turn_dir / name, maximums)
    _scan_yaml(interventions_path, maximums)
    return {kind: f"{kind}_{number + 1:04d}" for kind, number in maximums.items()}


def restore_resume_state(runs_dir: Path, interventions_path: Path) -> ResumeState:
    last_applied_turn: int | None = None
    pending_review_turn: int | None = None
    for turn_dir in _turn_dirs(runs_dir):
        if not _LIVE_TURN_RE.match(turn_dir.name):
            continue
        status = read_turn_status(turn_dir)
        if status == TurnStatus.APPLIED:
            last_applied_turn = max(last_applied_turn or 0, _turn_number(turn_dir))
        elif status in UNRESOLVED_STATUSES:
            pending_review_turn = _turn_number(turn_dir)
            break
    return ResumeState(
        last_applied_turn=last_applied_turn,
        pending_review_turn=pending_review_turn,
        rng_draws_consumed=total_rng_draws_consumed(runs_dir),
        next_ids=restore_next_id_counters(runs_dir, interventions_path),
    )
