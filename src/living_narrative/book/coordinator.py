"""Transaction-backed application of reviewed long-form plan proposals."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from living_narrative.book.planning import BookPlanProposal, proposal_to_state_diff
from living_narrative.state.diff import fsync_directory
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import (
    RecoveryError,
    RecoveryState,
    classify_recovery_state,
    commit_state_diff,
    project_lock,
    read_commit_intent,
)


class BookPlanApplyResult(BaseModel):
    diff_id: str
    journal_dir: Path


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def apply_book_plan_proposal(
    workspace_root: Path,
    proposal: BookPlanProposal,
) -> BookPlanApplyResult:
    """Persist an accepted proposal through the same journal-before-state protocol as turns.

    The dedicated journal preserves the proposal and state diff before the commit intent.
    Repeating a completed application is idempotent; unsafe incomplete journals surface as a
    recovery error instead of silently replacing state.
    """
    state_dir = workspace_root / "state"
    journal_dir = workspace_root / "runs" / ".transactions" / proposal.proposal_id
    diff = proposal_to_state_diff(proposal, turn=0)

    with project_lock(workspace_root):
        recovery = classify_recovery_state(journal_dir, state_dir, apply=True)
        if recovery in {RecoveryState.BLOCKED, RecoveryState.QUARANTINE}:
            raise RecoveryError(f"book proposal journal cannot be recovered: {journal_dir}")
        existing = read_commit_intent(journal_dir)
        if existing is not None and (journal_dir / "meta.yaml").exists():
            return BookPlanApplyResult(diff_id=existing.diff_id, journal_dir=journal_dir)

        def write_artifacts() -> None:
            _atomic_write_yaml(journal_dir / "proposal.yaml", proposal.model_dump(mode="json"))
            _atomic_write_yaml(journal_dir / "state_diff.yaml", diff.model_dump(mode="json"))

        result = commit_state_diff(
            StateStore.load(state_dir),
            diff,
            state_dir,
            journal_dir,
            meta={"kind": "book_plan_proposal", "proposal_id": proposal.proposal_id},
            on_commit=write_artifacts,
        )
    return BookPlanApplyResult(diff_id=result.inverse_diff.id, journal_dir=journal_dir)
