"""Read-only long-form cockpit projections for CLI or web presentation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from living_narrative.book.scheduler import schedule_next_chapter
from living_narrative.state.models import ChapterLifecycle, WorldStateBundle


class CockpitChapter(BaseModel):
    chapter_id: str
    act_id: str
    planned_goal: str
    lifecycle: ChapterLifecycle | None = None


class BookCockpit(BaseModel):
    premise: str
    audience: str
    active_chapter_id: str | None = None
    next_action: str
    chapters: list[CockpitChapter] = Field(default_factory=list)


def build_book_cockpit(bundle: WorldStateBundle) -> BookCockpit:
    """Return a UI-safe book view without copying GM or character-private data."""
    lifecycle_by_id = {chapter.id: chapter.lifecycle for chapter in bundle.book_ledger.chapters}
    schedule = schedule_next_chapter(bundle.book_ledger)
    return BookCockpit(
        premise=bundle.book_plan.premise,
        audience=bundle.book_plan.audience,
        active_chapter_id=bundle.book_ledger.active_chapter_id,
        next_action=schedule.action.value,
        chapters=[
            CockpitChapter(
                chapter_id=chapter.id,
                act_id=chapter.act_id,
                planned_goal=chapter.planned_goal,
                lifecycle=lifecycle_by_id.get(chapter.id),
            )
            for chapter in bundle.book_plan.chapters
        ],
    )
