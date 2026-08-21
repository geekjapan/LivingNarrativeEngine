"""Read-only long-form cockpit projections for CLI or web presentation."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from living_narrative.book.production_observability import ProductionOperationalMetrics
from living_narrative.book.scheduler import (
    IN_FLIGHT_CHAPTER_LIFECYCLES,
    NextChapterAction,
    schedule_next_chapter,
)
from living_narrative.state.models import ChapterLifecycle, WorldStateBundle


class CockpitChapter(BaseModel):
    chapter_id: str
    act_id: str
    planned_goal: str
    lifecycle: ChapterLifecycle | None = None
    target_min_words: int
    target_max_words: int
    startable: bool = False


class BookBudgetCockpit(BaseModel):
    """Reader-safe budget state for production decisions, without prompts or provider secrets."""

    status: str
    reason: str | None = None
    price_version: str | None = None
    actual_usd: Decimal | None = None
    estimated_usd: Decimal | None = None
    variance_usd: Decimal | None = None
    forecast_usd: Decimal | None = None
    remaining_hard_usd: Decimal | None = None
    resume_allowed: bool = False


class BookCockpit(BaseModel):
    premise: str
    audience: str
    can_operate: bool = False
    active_chapter_id: str | None = None
    next_action: str
    chapters: list[CockpitChapter] = Field(default_factory=list)
    budget: BookBudgetCockpit | None = None
    operations: ProductionOperationalMetrics | None = None


def build_book_cockpit(bundle: WorldStateBundle, *, can_operate: bool = False) -> BookCockpit:
    """Return a UI-safe book view without copying GM or character-private data.

    ``can_operate`` mirrors the API's authoring-mode gate so the UI does not offer controls
    whose only outcome would be a 403.
    """
    lifecycle_by_id = {chapter.id: chapter.lifecycle for chapter in bundle.book_ledger.chapters}
    schedule = schedule_next_chapter(bundle.book_ledger)
    in_flight = any(
        lifecycle in IN_FLIGHT_CHAPTER_LIFECYCLES for lifecycle in lifecycle_by_id.values()
    )
    return BookCockpit(
        can_operate=can_operate,
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
                target_min_words=chapter.target_word_range.min_words,
                target_max_words=chapter.target_word_range.max_words,
                startable=(
                    can_operate
                    and lifecycle_by_id.get(chapter.id) is ChapterLifecycle.PLANNED
                    and not in_flight
                    and schedule.action is NextChapterAction.START
                    and schedule.chapter_id == chapter.id
                ),
            )
            for chapter in bundle.book_plan.chapters
        ],
    )
