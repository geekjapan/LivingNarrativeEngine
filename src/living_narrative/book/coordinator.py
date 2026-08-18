"""Transaction-backed application of long-form plans and chapter production changes."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from living_narrative.book.artifacts import load_chapter_artifacts, save_chapter_artifacts
from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.planning import BookPlanProposal, proposal_to_state_diff
from living_narrative.book.review import ChapterReview, ChapterReviewDecision
from living_narrative.book.scheduler import schedule_next_chapter
from living_narrative.state.diff import StateDiff, StateDiffChange, fsync_directory
from living_narrative.state.models import ChapterLifecycle, Visibility
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


class ChapterProductionResult(BookPlanApplyResult):
    chapter_id: str
    lifecycle: ChapterLifecycle


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


def _assert_recoverable(journal_dir: Path, state_dir: Path) -> str | None:
    recovery = classify_recovery_state(journal_dir, state_dir, apply=True)
    if recovery in {RecoveryState.BLOCKED, RecoveryState.QUARANTINE}:
        raise RecoveryError(f"book transaction cannot be recovered: {journal_dir}")
    intent = read_commit_intent(journal_dir)
    if intent is not None and (journal_dir / "meta.yaml").exists():
        return intent.diff_id
    return None


def apply_book_plan_proposal(
    workspace_root: Path,
    proposal: BookPlanProposal,
) -> BookPlanApplyResult:
    """Persist an accepted proposal through the same journal-before-state protocol as turns."""
    state_dir = workspace_root / "state"
    journal_dir = workspace_root / "runs" / ".transactions" / proposal.proposal_id
    diff = proposal_to_state_diff(proposal, turn=0)

    with project_lock(workspace_root):
        existing_diff_id = _assert_recoverable(journal_dir, state_dir)
        if existing_diff_id is not None:
            return BookPlanApplyResult(diff_id=existing_diff_id, journal_dir=journal_dir)

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


def _chapter_transition(
    workspace_root: Path,
    chapter_id: str,
    lifecycle: ChapterLifecycle,
    *,
    journal_key: str = "",
    review_decision: str | None = None,
    candidate: ChapterCandidate | None = None,
    review: ChapterReview | None = None,
) -> ChapterProductionResult:
    """Commit one validated chapter lifecycle transition and its durable artifacts."""
    if candidate is not None and review is None:
        raise ValueError("candidate persistence requires a chapter review")
    if candidate is not None and candidate.chapter_id != chapter_id:
        raise ValueError("candidate chapter_id does not match lifecycle target")
    if review is not None and review.chapter_id != chapter_id:
        raise ValueError("review chapter_id does not match lifecycle target")

    state_dir = workspace_root / "state"
    candidate_suffix = (
        hashlib.sha256(candidate.markdown.encode("utf-8")).hexdigest()[:16]
        if candidate is not None
        else journal_key
    )
    journal_suffix = f"_{candidate_suffix}" if candidate_suffix else ""
    journal_dir = (
        workspace_root
        / "runs"
        / ".transactions"
        / f"chapter_{chapter_id}_{lifecycle}{journal_suffix}"
    )
    with project_lock(workspace_root):
        existing_diff_id = _assert_recoverable(journal_dir, state_dir)
        if existing_diff_id is not None:
            return ChapterProductionResult(
                diff_id=existing_diff_id,
                journal_dir=journal_dir,
                chapter_id=chapter_id,
                lifecycle=lifecycle,
            )
        bundle = StateStore.load(state_dir)
        ledger = bundle.book_ledger.transition(chapter_id, lifecycle)
        if lifecycle is ChapterLifecycle.RUNNING:
            ledger.active_chapter_id = chapter_id
        if review_decision is not None:
            ledger.chapter(chapter_id).review_decision = review_decision
        if lifecycle in {ChapterLifecycle.ACCEPTED, ChapterLifecycle.REVISING}:
            ledger.next_action = schedule_next_chapter(ledger).action.value
            if lifecycle is ChapterLifecycle.ACCEPTED:
                ledger.active_chapter_id = None
        diff = StateDiff(
            id="diff_0000",
            turn=0,
            changes=[
                StateDiffChange(
                    target="book_ledger",
                    op="set",
                    value=ledger.model_dump(mode="json"),
                    visibility=Visibility.GM_ONLY,
                )
            ],
        )

        def write_artifacts() -> None:
            if candidate is not None and review is not None:
                save_chapter_artifacts(workspace_root / "books" / "chapters", candidate, review)
            _atomic_write_yaml(
                journal_dir / "chapter_transition.yaml",
                {
                    "chapter_id": chapter_id,
                    "lifecycle": lifecycle.value,
                    "review_decision": review_decision,
                },
            )

        result = commit_state_diff(
            bundle,
            diff,
            state_dir,
            journal_dir,
            meta={
                "kind": "chapter_lifecycle",
                "chapter_id": chapter_id,
                "lifecycle": lifecycle.value,
            },
            on_commit=write_artifacts,
        )
    return ChapterProductionResult(
        diff_id=result.inverse_diff.id,
        journal_dir=journal_dir,
        chapter_id=chapter_id,
        lifecycle=lifecycle,
    )


def start_chapter_production(workspace_root: Path, chapter_id: str) -> ChapterProductionResult:
    """Reserve a planned chapter for production."""
    return _chapter_transition(workspace_root, chapter_id, ChapterLifecycle.RUNNING)


def record_chapter_candidate(
    workspace_root: Path,
    candidate: ChapterCandidate,
    review: ChapterReview,
) -> ChapterProductionResult:
    """Persist the candidate/review pair before it enters author review."""
    return _chapter_transition(
        workspace_root,
        candidate.chapter_id,
        ChapterLifecycle.CANDIDATE,
        candidate=candidate,
        review=review,
    )


def _current_candidate_key(workspace_root: Path, chapter_id: str) -> str:
    candidate_path = workspace_root / "books" / "chapters" / chapter_id / "candidate.md"
    if not candidate_path.is_file():
        raise ValueError(f"candidate artifact not found for {chapter_id}")
    return hashlib.sha256(candidate_path.read_bytes()).hexdigest()[:16]


def open_chapter_review(workspace_root: Path, chapter_id: str) -> ChapterProductionResult:
    """Move a durable candidate into the explicit author-review state."""
    return _chapter_transition(
        workspace_root,
        chapter_id,
        ChapterLifecycle.REVIEW,
        journal_key=_current_candidate_key(workspace_root, chapter_id),
    )


def accept_chapter_review(workspace_root: Path, chapter_id: str) -> ChapterProductionResult:
    """Accept a reviewed chapter as an immutable manuscript input."""
    _, review = load_chapter_artifacts(workspace_root / "books" / "chapters", chapter_id)
    if review.decision is not ChapterReviewDecision.ACCEPT:
        raise ValueError("cannot accept a non-accept review")
    return _chapter_transition(
        workspace_root,
        chapter_id,
        ChapterLifecycle.ACCEPTED,
        review_decision="accept",
    )


def request_chapter_revision(workspace_root: Path, chapter_id: str) -> ChapterProductionResult:
    """Return a reviewed chapter to revision without destroying its prior artifact."""
    return _chapter_transition(
        workspace_root,
        chapter_id,
        ChapterLifecycle.REVISING,
        journal_key=_current_candidate_key(workspace_root, chapter_id),
        review_decision="revise",
    )
