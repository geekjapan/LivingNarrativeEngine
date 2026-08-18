"""Transaction-backed application of long-form plans and chapter production changes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from living_narrative.book.artifacts import load_chapter_artifacts, save_chapter_artifacts
from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.continuity import advance_continuity_ledger
from living_narrative.book.lineage import (
    accept_chapter_attempt,
    load_chapter_lineage,
    record_chapter_attempt,
)
from living_narrative.book.planning import BookPlanProposal, proposal_to_state_diff
from living_narrative.book.review import ChapterReview, ChapterReviewDecision
from living_narrative.book.scheduler import IN_FLIGHT_CHAPTER_LIFECYCLES, schedule_next_chapter
from living_narrative.state.diff import StateDiff, StateDiffChange, fsync_directory
from living_narrative.state.models import (
    BookLedgerState,
    ChapterLifecycle,
    Visibility,
    WorldStateBundle,
)
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import (
    RecoveryError,
    RecoveryState,
    classify_recovery_state,
    commit_state_diff,
    project_lock,
    read_commit_intent,
)
from living_narrative.workspace.loader import WorkspacePaths


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


def _plan_generation(bundle: WorldStateBundle) -> str:
    payload = json.dumps(
        bundle.book_plan.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _reject_concurrent_chapter_start(ledger: BookLedgerState, chapter_id: str) -> None:
    in_flight = [
        chapter.id
        for chapter in ledger.chapters
        if chapter.id != chapter_id and chapter.lifecycle in IN_FLIGHT_CHAPTER_LIFECYCLES
    ]
    if in_flight:
        raise ValueError(f"chapter {in_flight[0]} is already in production")


def _workspace_dirs(workspace: Path | WorkspacePaths) -> tuple[Path, Path, Path]:
    """Resolve root/state/runs from either a workspace root or ``load_project()`` paths.

    ``workspace.state`` and ``workspace.runs`` are configurable, so a caller that already
    resolved them must be able to hand them over instead of having them re-derived here.
    """
    if isinstance(workspace, WorkspacePaths):
        return workspace.root, workspace.state, workspace.runs
    return workspace, workspace / "state", workspace / "runs"


def _assert_recoverable(journal_dir: Path, state_dir: Path) -> str | None:
    recovery = classify_recovery_state(journal_dir, state_dir, apply=True)
    if recovery in {RecoveryState.BLOCKED, RecoveryState.QUARANTINE}:
        raise RecoveryError(f"book transaction cannot be recovered: {journal_dir}")
    intent = read_commit_intent(journal_dir)
    if intent is not None and (journal_dir / "meta.yaml").exists():
        return intent.diff_id
    return None


def apply_book_plan_proposal(
    workspace: Path | WorkspacePaths,
    proposal: BookPlanProposal,
) -> BookPlanApplyResult:
    """Persist an accepted proposal through the same journal-before-state protocol as turns."""
    workspace_root, state_dir, runs_dir = _workspace_dirs(workspace)
    journal_dir = runs_dir / ".transactions" / proposal.proposal_id
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
    workspace: Path | WorkspacePaths,
    chapter_id: str,
    lifecycle: ChapterLifecycle,
    *,
    journal_key: str = "",
    review_decision: str | None = None,
    candidate: ChapterCandidate | None = None,
    review: ChapterReview | None = None,
    draft_run_id: str | None = None,
) -> ChapterProductionResult:
    """Commit one validated chapter lifecycle transition and its durable artifacts."""
    if candidate is not None and review is None:
        raise ValueError("candidate persistence requires a chapter review")
    if candidate is not None and candidate.chapter_id != chapter_id:
        raise ValueError("candidate chapter_id does not match lifecycle target")
    if review is not None and review.chapter_id != chapter_id:
        raise ValueError("review chapter_id does not match lifecycle target")

    workspace_root, state_dir, runs_dir = _workspace_dirs(workspace)
    candidate_suffix = (
        hashlib.sha256(candidate.markdown.encode("utf-8")).hexdigest()[:16]
        if candidate is not None
        else journal_key
    )
    journal_suffix = f"_{candidate_suffix}" if candidate_suffix else ""
    with project_lock(workspace_root):
        bundle = StateStore.load(state_dir)
        journal_dir = (
            runs_dir
            / ".transactions"
            / f"chapter_{_plan_generation(bundle)}_{chapter_id}_{lifecycle}{journal_suffix}"
        )
        existing_diff_id = _assert_recoverable(journal_dir, state_dir)
        if existing_diff_id is not None:
            return ChapterProductionResult(
                diff_id=existing_diff_id,
                journal_dir=journal_dir,
                chapter_id=chapter_id,
                lifecycle=lifecycle,
            )
        if lifecycle is ChapterLifecycle.RUNNING:
            _reject_concurrent_chapter_start(bundle.book_ledger, chapter_id)
        ledger = bundle.book_ledger.transition(chapter_id, lifecycle)
        if lifecycle is ChapterLifecycle.RUNNING:
            ledger.active_chapter_id = chapter_id
        if review_decision is not None:
            ledger.chapter(chapter_id).review_decision = review_decision
        if lifecycle in {ChapterLifecycle.ACCEPTED, ChapterLifecycle.REVISING}:
            ledger.next_action = schedule_next_chapter(ledger).action.value
            if lifecycle is ChapterLifecycle.ACCEPTED:
                lineage = load_chapter_lineage(workspace_root / "books" / "chapters", chapter_id)
                if not lineage.attempts:
                    raise ValueError("cannot accept a chapter without an immutable attempt")
                attempt = lineage.attempts[-1]
                chapter = bundle.book_plan.chapter(chapter_id)
                covered = (
                    attempt.review.semantic.required_threads_covered
                    if attempt.review.semantic is not None
                    else []
                )
                ledger = advance_continuity_ledger(
                    ledger,
                    ChapterCandidate(
                        chapter_id=chapter_id,
                        source_turns=attempt.source_turns,
                        markdown=attempt.candidate_markdown,
                    ),
                    required_thread_ids=list(chapter.required_thread_ids),
                    covered_thread_ids=covered,
                )
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
            chapters_root = workspace_root / "books" / "chapters"
            if candidate is not None and review is not None:
                save_chapter_artifacts(chapters_root, candidate, review)
                existing = load_chapter_lineage(chapters_root, chapter_id)
                candidate_hash = hashlib.sha256(candidate.markdown.encode("utf-8")).hexdigest()
                recorded_hashes = {attempt.candidate_sha256 for attempt in existing.attempts}
                if candidate_hash not in recorded_hashes:
                    record_chapter_attempt(
                        chapters_root, candidate, review, draft_run_id=draft_run_id
                    )
            if lifecycle is ChapterLifecycle.ACCEPTED:
                lineage = load_chapter_lineage(chapters_root, chapter_id)
                if not lineage.attempts:
                    raise ValueError("cannot accept a chapter without an immutable attempt")
                accept_chapter_attempt(
                    chapters_root, chapter_id, _reviewed_attempt_id(chapters_root, chapter_id)
                )
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


def start_chapter_production(
    workspace: Path | WorkspacePaths, chapter_id: str
) -> ChapterProductionResult:
    """Reserve a planned chapter for production."""
    return _chapter_transition(workspace, chapter_id, ChapterLifecycle.RUNNING)


def record_chapter_candidate(
    workspace: Path | WorkspacePaths,
    candidate: ChapterCandidate,
    review: ChapterReview,
    *,
    draft_run_id: str | None = None,
) -> ChapterProductionResult:
    """Persist the candidate/review pair before it enters author review.

    ``draft_run_id`` ties the immutable attempt back to the persisted request, prompt and
    response of the draft run that produced it.
    """
    return _chapter_transition(
        workspace,
        candidate.chapter_id,
        ChapterLifecycle.CANDIDATE,
        candidate=candidate,
        review=review,
        draft_run_id=draft_run_id,
    )


def _reviewed_attempt_id(chapters_root: Path, chapter_id: str) -> str:
    """Resolve the attempt holding the body under review.

    A retained lineage can gain attempts out of review order (a replacement plan reusing a
    chapter ID, or a revision recorded while an older candidate is still under review), so list
    position is not evidence of what the author accepted.
    """
    lineage = load_chapter_lineage(chapters_root, chapter_id)
    if not lineage.attempts:
        raise ValueError("cannot accept a chapter without an immutable attempt")
    candidate_path = chapters_root / chapter_id / "candidate.md"
    if candidate_path.is_file():
        reviewed = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        match = next((item for item in lineage.attempts if item.candidate_sha256 == reviewed), None)
        if match is not None:
            return match.id
    return lineage.attempts[-1].id


def _current_candidate_key(workspace: Path | WorkspacePaths, chapter_id: str) -> str:
    root = _workspace_dirs(workspace)[0]
    candidate_path = root / "books" / "chapters" / chapter_id / "candidate.md"
    if not candidate_path.is_file():
        raise ValueError(f"candidate artifact not found for {chapter_id}")
    return hashlib.sha256(candidate_path.read_bytes()).hexdigest()[:16]


def open_chapter_review(
    workspace: Path | WorkspacePaths, chapter_id: str
) -> ChapterProductionResult:
    """Move a durable candidate into the explicit author-review state."""
    return _chapter_transition(
        workspace,
        chapter_id,
        ChapterLifecycle.REVIEW,
        journal_key=_current_candidate_key(workspace, chapter_id),
    )


def accept_chapter_review(
    workspace: Path | WorkspacePaths, chapter_id: str
) -> ChapterProductionResult:
    """Accept a reviewed chapter as an immutable manuscript input."""
    root = _workspace_dirs(workspace)[0]
    _, review = load_chapter_artifacts(root / "books" / "chapters", chapter_id)
    if review.decision is not ChapterReviewDecision.ACCEPT:
        raise ValueError("cannot accept a non-accept review")
    return _chapter_transition(
        workspace,
        chapter_id,
        ChapterLifecycle.ACCEPTED,
        review_decision="accept",
    )


def request_chapter_revision(
    workspace: Path | WorkspacePaths, chapter_id: str
) -> ChapterProductionResult:
    """Return a reviewed chapter to revision without destroying its prior artifact."""
    return _chapter_transition(
        workspace,
        chapter_id,
        ChapterLifecycle.REVISING,
        journal_key=_current_candidate_key(workspace, chapter_id),
        review_decision="revise",
    )
