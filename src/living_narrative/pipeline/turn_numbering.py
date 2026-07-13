"""Turn number resolution and discarded-dir eviction (spec-foundation.md D111/D112).

Exposed as public utilities (not TurnPipeline-internal) so ``add-session-autonomy``'s
GM review gate can reuse them for ``rerun_turn`` without going through the 8-phase driver.
"""

import re
from pathlib import Path

import yaml

from living_narrative.pipeline.errors import UnresolvedTurnError
from living_narrative.pipeline.status import UNRESOLVED_STATUSES, TurnStatus

_TURN_DIR_RE = re.compile(r"^turn_(\d+)$")
ANY_TURN_DIR_RE = re.compile(r"^turn_(\d+)(?:_discarded_\d+)?$")
_DISCARDED_TURN_DIR_RE = re.compile(r"^turn_(\d+)_discarded_\d+$")


def turn_dir_path(runs_dir: Path, turn: int) -> Path:
    return runs_dir / f"turn_{turn:04d}"


def read_turn_status(turn_dir: Path) -> TurnStatus | None:
    """Return the turn's status, or ``None`` if ``meta.yaml`` is missing/unparseable."""
    meta_path = turn_dir / "meta.yaml"
    if not meta_path.exists():
        return None
    try:
        data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    try:
        return TurnStatus(data.get("status"))
    except ValueError:
        return None


def existing_turn_numbers(runs_dir: Path) -> list[int]:
    """Sorted ``turn_NNNN`` numbers (excludes ``_discarded_``/``_rolledback_`` dirs).

    Public: also used by ``session/rollback.py`` to find the current latest turn.
    """
    if not runs_dir.exists():
        return []
    numbers = [
        int(match.group(1))
        for entry in runs_dir.iterdir()
        if entry.is_dir() and (match := _TURN_DIR_RE.match(entry.name))
    ]
    return sorted(numbers)


def determine_next_turn_number(runs_dir: Path) -> int:
    """ "Last applied turn + 1", blocking on an unresolved latest turn (SHALL/MUST NOT)."""
    numbers = existing_turn_numbers(runs_dir)
    discarded_numbers = []
    if runs_dir.exists():
        discarded_numbers = [
            int(match.group(1))
            for entry in runs_dir.iterdir()
            if entry.is_dir() and (match := _DISCARDED_TURN_DIR_RE.match(entry.name))
        ]
    if not numbers:
        return max(discarded_numbers, default=0) or 1

    latest = numbers[-1]
    status = read_turn_status(turn_dir_path(runs_dir, latest))
    if status is None:
        raise UnresolvedTurnError(f"turn_{latest:04d} exists without a valid meta.yaml")
    if status in UNRESOLVED_STATUSES:
        raise UnresolvedTurnError(f"turn_{latest:04d} is unresolved (status={status.value})")
    if status is TurnStatus.FAILED:
        return latest
    if discarded_numbers and max(discarded_numbers) > latest:
        return max(discarded_numbers)
    return latest + 1


def discard_turn_directory(turn_dir: Path) -> Path:
    """Rename an existing turn dir to ``turn_NNNN_discarded_<n>`` (D112, never overwritten)."""
    n = 1
    while True:
        candidate = turn_dir.parent / f"{turn_dir.name}_discarded_{n}"
        if not candidate.exists():
            break
        n += 1
    turn_dir.rename(candidate)
    return candidate


def rollback_turn_directory(turn_dir: Path) -> Path:
    """Rename a rolled-back turn dir to ``turn_NNNN_rolledback_<n>`` (Issue 018).

    Mirrors ``discard_turn_directory`` (D112 spirit: never destroy turn history, only
    rename it aside) but with a distinct suffix so it does NOT match ``ANY_TURN_DIR_RE``:
    rolled-back turns must fall out of RNG-draw/roll-id accounting (``pipeline/rng_state.py``)
    and out of ``session/resume.py``'s next-id/last-applied-turn scans, since a rollback
    means those turns' rolls/draws are no longer part of the project's live history.
    """
    n = 1
    while True:
        candidate = turn_dir.parent / f"{turn_dir.name}_rolledback_{n}"
        if not candidate.exists():
            break
        n += 1
    turn_dir.rename(candidate)
    return candidate
