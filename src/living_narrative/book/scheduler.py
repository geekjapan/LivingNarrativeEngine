"""Deterministic next-action selection for serial chapter production."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from living_narrative.state.models import BookLedgerState, ChapterLifecycle


class NextChapterAction(StrEnum):
    START = "start"
    REVISE = "revise"
    WAIT_FOR_REVIEW = "wait_for_review"
    COMPLETE = "complete"


ACTIVE_PRODUCTION_LIFECYCLES = {
    ChapterLifecycle.RUNNING,
    ChapterLifecycle.CANDIDATE,
    ChapterLifecycle.REVIEW,
}
IN_FLIGHT_CHAPTER_LIFECYCLES = {
    *ACTIVE_PRODUCTION_LIFECYCLES,
    ChapterLifecycle.REVISING,
}


class ChapterScheduleDecision(BaseModel):
    action: NextChapterAction
    chapter_id: str | None = None


def schedule_next_chapter(ledger: BookLedgerState) -> ChapterScheduleDecision:
    """Prefer unfinished revision work, then the earliest planned chapter."""
    for chapter in ledger.chapters:
        if chapter.lifecycle == ChapterLifecycle.REVISING:
            return ChapterScheduleDecision(action=NextChapterAction.REVISE, chapter_id=chapter.id)
    if any(chapter.lifecycle in ACTIVE_PRODUCTION_LIFECYCLES for chapter in ledger.chapters):
        return ChapterScheduleDecision(action=NextChapterAction.WAIT_FOR_REVIEW)
    for chapter in ledger.chapters:
        if chapter.lifecycle == ChapterLifecycle.PLANNED:
            return ChapterScheduleDecision(action=NextChapterAction.START, chapter_id=chapter.id)
    return ChapterScheduleDecision(action=NextChapterAction.COMPLETE)
