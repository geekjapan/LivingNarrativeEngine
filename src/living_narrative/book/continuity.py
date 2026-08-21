"""Deterministic reader-safe continuity digest for accepted book chapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from living_narrative.state.models import (
    BookActContinuitySummary,
    BookCharacterArcSummary,
    BookContinuityEntry,
    BookContinuityState,
    BookLedgerState,
    CharacterArcTarget,
)

if TYPE_CHECKING:
    from living_narrative.book.chapters import ChapterCandidate


def strip_chapter_scaffolding(markdown: str) -> str:
    """Remove compile frontmatter, heading, and planned-goal prompt from a chapter artifact."""
    body = markdown
    if body.startswith("---\n"):
        _, separator, remainder = body.partition("\n---\n")
        body = remainder if separator else body
    lines = body.splitlines()
    index = 0
    while index < len(lines) and lines[index].strip() == "":
        index += 1
    if index < len(lines) and lines[index].startswith("# "):
        index += 1
    while index < len(lines) and lines[index].strip() == "":
        index += 1
    if index < len(lines) and lines[index].startswith("> Planned goal:"):
        index += 1
    while index < len(lines) and lines[index].strip() == "":
        index += 1
    return "\n".join(lines[index:])


def _reader_body(markdown: str) -> str:
    """Remove compile scaffolding and collapse whitespace for a bounded digest."""
    return " ".join(strip_chapter_scaffolding(markdown).split())


def advance_continuity_ledger(
    ledger: BookLedgerState,
    candidate: ChapterCandidate,
    *,
    required_thread_ids: list[str],
    covered_thread_ids: list[str],
    act_id: str | None = None,
    character_arc_targets: list[CharacterArcTarget] | None = None,
    covered_character_arc_target_ids: list[str] | None = None,
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
    chapter_summary = _reader_body(candidate.markdown)[:max_summary_chars]
    entry = BookContinuityEntry(
        chapter_id=candidate.chapter_id,
        summary=chapter_summary,
        covered_thread_ids=covered,
        open_thread_ids=open_threads,
    )
    updated = ledger.model_copy(deep=True)
    act_summaries = list(updated.continuity.act_summaries)
    if act_id is not None:
        previous_act = next((item for item in act_summaries if item.act_id == act_id), None)
        act_summaries = [item for item in act_summaries if item.act_id != act_id]
        previous_chapter_ids = previous_act.chapter_ids if previous_act else []
        act_summary_parts = [previous_act.summary if previous_act else "", chapter_summary]
        act_summaries.append(
            BookActContinuitySummary(
                act_id=act_id,
                chapter_ids=[*previous_chapter_ids, candidate.chapter_id],
                summary=" ".join(part for part in act_summary_parts if part)[:max_summary_chars],
                open_thread_ids=open_threads,
            )
        )
    character_arcs = list(updated.continuity.character_arcs)
    covered_arc_ids = set(covered_character_arc_target_ids or [])
    for target in character_arc_targets or []:
        if target.character_id not in covered_arc_ids:
            continue
        previous_arc = next(
            (item for item in character_arcs if item.character_id == target.character_id), None
        )
        character_arcs = [
            item for item in character_arcs if item.character_id != target.character_id
        ]
        previous_chapter_ids = previous_arc.chapter_ids if previous_arc else []
        previous_deltas = previous_arc.observed_deltas if previous_arc else []
        character_arcs.append(
            BookCharacterArcSummary(
                character_id=target.character_id,
                chapter_ids=[*previous_chapter_ids, candidate.chapter_id],
                observed_deltas=[*previous_deltas, target.delta],
            )
        )
    updated.continuity = BookContinuityState(
        entries=[*updated.continuity.entries, entry],
        open_thread_ids=open_threads,
        act_summaries=act_summaries,
        character_arcs=character_arcs,
    )
    return updated


def render_hierarchical_continuity_context(
    continuity: BookContinuityState,
    *,
    act_id: str,
    character_ids: list[str],
    max_chars: int = 2_000,
) -> str:
    """Render current-act and relevant character evidence within a deterministic budget."""
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")
    segments: list[str] = []
    act = next((item for item in continuity.act_summaries if item.act_id == act_id), None)
    if act is not None and act.summary:
        segments.append(f"Act {act_id}: {act.summary}")
    arcs_by_character = {item.character_id: item for item in continuity.character_arcs}
    for character_id in character_ids:
        arc = arcs_by_character.get(character_id)
        if arc is not None and arc.observed_deltas:
            segments.append(f"Character {character_id}: {'; '.join(arc.observed_deltas)}")
    if continuity.open_thread_ids:
        segments.append(f"Open threads: {', '.join(continuity.open_thread_ids)}")
    return "\n".join(segments)[:max_chars]


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
