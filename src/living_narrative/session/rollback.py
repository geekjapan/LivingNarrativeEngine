"""Rollback / branch orchestration (Issue 018).

Rewinds project state using each applied turn's saved inverse diff
(``state/diff.py``'s ``rollback()``/``load_inverse_diff()``). Rolled-back turn dirs are
never deleted, only renamed aside to ``turn_NNNN_rolledback_<n>`` (D112 spirit: never
destroy turn history). ``branch`` is a plain copy-then-rewind: copy the whole project dir,
then run the same rollback against the copy, leaving the original untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from living_narrative.pipeline.status import UNRESOLVED_STATUSES, TurnStatus
from living_narrative.pipeline.turn_numbering import (
    existing_turn_numbers,
    read_turn_status,
    turn_dir_path,
)
from living_narrative.state.diff import InverseStateDiff, StateDiff, load_inverse_diff
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import (
    RecoveryError,
    RecoveryState,
    classify_recovery_state,
    commit_state_diff,
    finalize_rollback_renames,
    latest_turn_directory,
    project_lock,
    recover_rollback_journals,
)
from living_narrative.workspace.copy import WorkspaceCopyError, copy_directory_atomic
from living_narrative.workspace.loader import WorkspacePaths


class RollbackError(ValueError):
    """A rollback/branch request is invalid for the project's current turn history."""


@dataclass(frozen=True)
class RollbackPlan:
    """The turns a rollback would affect, computed without touching the filesystem."""

    current_turn: int
    to_turn: int
    rolled_back_turns: list[int]


@dataclass(frozen=True)
class RollbackResult:
    current_turn: int
    to_turn: int
    rolled_back_turns: list[int]
    rolled_back_dirs: list[Path]


def plan_rollback(runs_dir: Path, to_turn: int) -> RollbackPlan:
    """Validate a ``--to-turn`` request and report what it would roll back.

    Raises ``RollbackError`` for any of the three guards (Issue 018 design §3): the
    latest turn is unresolved (pending_review/stopped_for_review), ``to_turn`` is not
    strictly less than the current applied turn, or an ``inverse_diff.yaml`` is missing
    somewhere in the range being rolled back (no partial rollback).
    """
    numbers = existing_turn_numbers(runs_dir)
    if not numbers:
        raise RollbackError("no turns recorded yet; nothing to roll back")

    latest = numbers[-1]
    latest_status = read_turn_status(turn_dir_path(runs_dir, latest))
    if latest_status in UNRESOLVED_STATUSES:
        raise RollbackError(
            f"turn {latest} is unresolved (status={latest_status.value}); "
            "resolve it first with `living-narrative review`"
        )
    # A FAILED tail never committed a diff, so it isn't part of the applied history.
    current_turn = latest if latest_status == TurnStatus.APPLIED else latest - 1

    if to_turn < 0:
        raise RollbackError("--to-turn must be >= 0")
    if to_turn >= current_turn:
        raise RollbackError(
            f"--to-turn ({to_turn}) must be less than the current applied turn ({current_turn})"
        )

    rolled_back_turns = list(range(to_turn + 1, current_turn + 1))
    missing = [
        turn
        for turn in rolled_back_turns
        if not (turn_dir_path(runs_dir, turn) / "inverse_diff.yaml").exists()
    ]
    if missing:
        missing_str = ", ".join(str(turn) for turn in missing)
        raise RollbackError(
            f"missing inverse_diff.yaml for turn(s) {missing_str}; "
            "partial rollback is not supported"
        )

    return RollbackPlan(
        current_turn=current_turn, to_turn=to_turn, rolled_back_turns=rolled_back_turns
    )


def execute_rollback(paths: WorkspacePaths, plan: RollbackPlan) -> RollbackResult:
    """Apply ``plan``: rewind state to ``plan.to_turn`` and rename the rolled-back dirs.

    ``plan`` carries only turn numbers (no paths), so a plan computed against one
    project's ``runs_dir`` can be replayed verbatim against a byte-identical copy
    (``branch``'s use case).
    """
    with project_lock(paths.root):
        recover_rollback_journals(paths.runs, paths.state)
        plan = plan_rollback(paths.runs, plan.to_turn)
        journal_dir = (
            paths.runs
            / ".transactions"
            / (f"rollback_{plan.current_turn:04d}_to_{plan.to_turn:04d}")
        )
        journal_recovery_state = classify_recovery_state(journal_dir, paths.state)
        if journal_recovery_state in {RecoveryState.QUARANTINE, RecoveryState.BLOCKED}:
            raise RecoveryError(
                "cannot mutate project while rollback journal recovery state is "
                f"{journal_recovery_state.value}",
                target="rollback_journal",
                quarantine=journal_recovery_state is RecoveryState.QUARANTINE,
            )
        recovery_state = classify_recovery_state(
            latest_turn_directory(paths.runs),
            paths.state,
        )
        if recovery_state in {RecoveryState.QUARANTINE, RecoveryState.BLOCKED}:
            raise RecoveryError(
                f"cannot mutate project while recovery state is {recovery_state.value}",
                quarantine=recovery_state is RecoveryState.QUARANTINE,
            )
        inverse_diffs: list[InverseStateDiff] = [
            load_inverse_diff(turn_dir_path(paths.runs, turn) / "inverse_diff.yaml")
            for turn in plan.rolled_back_turns
        ]
        bundle = StateStore.load(paths.state)
        rollback_diff = StateDiff(
            id=f"diff_{plan.current_turn:04d}",
            turn=plan.to_turn,
            changes=[
                change
                for inverse_diff in reversed(inverse_diffs)
                for change in inverse_diff.changes
            ],
        )
        commit_state_diff(
            bundle,
            rollback_diff,
            paths.state,
            journal_dir,
            meta={
                "turn": plan.to_turn,
                "commit_mode": "rollback",
                "rollback_from_turn": plan.current_turn,
            },
        )

        rolled_back_dirs = finalize_rollback_renames(
            paths.runs,
            journal_dir,
            from_turn=plan.current_turn,
            to_turn=plan.to_turn,
        )
        return RollbackResult(
            current_turn=plan.current_turn,
            to_turn=plan.to_turn,
            rolled_back_turns=plan.rolled_back_turns,
            rolled_back_dirs=rolled_back_dirs,
        )


def copy_project_for_branch(source_root: Path, output_dir: Path) -> Path:
    """Copy the whole project dir (``project.yaml`` + ``workspace/``) to ``output_dir``.

    Returns the branch's ``project.yaml`` path. Raises ``RollbackError`` if
    ``output_dir`` already exists (branches never merge into an existing directory).
    """
    if output_dir.exists():
        raise RollbackError(f"branch output already exists: {output_dir}")
    try:
        copy_directory_atomic(source_root, output_dir)
    except WorkspaceCopyError as exc:
        if output_dir.exists():
            raise RollbackError(f"branch output already exists: {output_dir}") from exc
        raise RollbackError(str(exc)) from exc
    return output_dir / "project.yaml"


def append_branch_title_suffix(project_path: Path, from_turn: int) -> None:
    """Append `` (branch@N)`` to the branched copy's ``project.yaml`` title."""
    data = yaml.safe_load(project_path.read_text(encoding="utf-8")) or {}
    data["title"] = f"{data.get('title', '')} (branch@{from_turn})"
    project_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


__all__ = [
    "RollbackError",
    "RollbackPlan",
    "RollbackResult",
    "append_branch_title_suffix",
    "copy_project_for_branch",
    "execute_rollback",
    "plan_rollback",
]
