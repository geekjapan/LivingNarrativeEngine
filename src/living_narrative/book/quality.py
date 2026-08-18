"""Deterministic book-level quality gates built from chapter review artifacts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from living_narrative.book.review import ChapterReview, ChapterReviewDecision


class BookQualityDecision(StrEnum):
    ACCEPT = "accept"
    BLOCK = "block"


class BookQualityReport(BaseModel):
    decision: BookQualityDecision
    planned_chapter_ids: list[str] = Field(default_factory=list)
    reviewed_chapter_ids: list[str] = Field(default_factory=list)
    blocking_chapter_ids: list[str] = Field(default_factory=list)


def evaluate_book_quality(
    *,
    planned_chapter_ids: list[str],
    reviews: list[ChapterReview],
) -> BookQualityReport:
    """Block publication unless every planned chapter has an accepted review."""
    reviews_by_chapter = {review.chapter_id: review for review in reviews}
    blockers = [
        chapter_id
        for chapter_id in planned_chapter_ids
        if reviews_by_chapter.get(chapter_id) is None
        or reviews_by_chapter[chapter_id].decision != ChapterReviewDecision.ACCEPT
    ]
    return BookQualityReport(
        decision=BookQualityDecision.BLOCK if blockers else BookQualityDecision.ACCEPT,
        planned_chapter_ids=planned_chapter_ids,
        reviewed_chapter_ids=sorted(reviews_by_chapter),
        blocking_chapter_ids=blockers,
    )
