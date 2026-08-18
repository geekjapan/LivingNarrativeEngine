"""Deterministic reader-safe continuity digest for accepted book chapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from living_narrative.state.models import BookContinuityEntry, BookContinuityState, BookLedgerState

if TYPE_CHECKING:
    from living_narrative.book.chapters import ChapterCandidate


def _reader_body(markdown: str) -> str:
    """Remove the optional compile frontmatter and heading from a reader artifact."""
    body = markdown
    if body.startswith("---\n"):
        _, separator, remainder = body.partition("\n---\n")
        body = remainder if separator else body
    if body.startswith("# "):
        _, _, body = body.partition("\n")
    return " ".join(body.split())


def advance_continuity_ledger(
    ledger: BookLedgerState,
    candidate: ChapterCandidate,
    *,
    required_thread_ids: list[str],
    covered_thread_ids: list[str],
    max_summary_chars: int = 1_200,
) -> BookLedgerState:
    """Return a copied ledger with one accepted chapter's bounded continuity entry.

    The candidate is a reader-facing manuscript artifact; no hidden state is inspected or copied.
    """
    if max_summary_chars < 1:
        raise ValueError("max_summary_chars must be at least 1")
    if any(entry.chapter_id == candidate.chapter_id for entry in ledger.continuity.entries):
        raise ValueError(f"continuity entry already exists for {candidate.chapter_id}")
    covered_set = set(covered_thread_ids)
    covered = [thread_id for thread_id in required_thread_ids if thread_id in covered_set]
    newly_open = [thread_id for thread_id in required_thread_ids if thread_id not in covered_set]
    open_threads = [
        thread_id
        for thread_id in dict.fromkeys([*ledger.continuity.open_thread_ids, *newly_open])
        if thread_id not in covered_set
    ]
    entry = BookContinuityEntry(
        chapter_id=candidate.chapter_id,
        summary=_reader_body(candidate.markdown)[:max_summary_chars],
        covered_thread_ids=covered,
        open_thread_ids=open_threads,
    )
    updated = ledger.model_copy(deep=True)
    updated.continuity = BookContinuityState(
        entries=[*updated.continuity.entries, entry],
        open_thread_ids=open_threads,
    )
    return updated


def render_continuity_digest(continuity: BookContinuityState, *, max_chars: int = 4_000) -> str:
    """Render the newest reader-safe summaries within a deterministic size budget."""
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")
    selected: list[str] = []
    remaining = max_chars
    for entry in reversed(continuity.entries):
        if remaining <= 0:
            break
        segment = entry.summary[:remaining]
        selected.append(segment)
        remaining -= len(segment)
    return "\n".join(reversed(selected))
