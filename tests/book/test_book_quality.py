from __future__ import annotations

from living_narrative.book.quality import BookQualityDecision, evaluate_book_quality
from living_narrative.book.review import (
    ChapterReview,
    ChapterReviewDecision,
    ChapterReviewMetrics,
)


def _review(chapter_id: str, decision: ChapterReviewDecision) -> ChapterReview:
    return ChapterReview(
        chapter_id=chapter_id,
        decision=decision,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
        reasons=[] if decision == ChapterReviewDecision.ACCEPT else ["revision required"],
    )


def test_book_quality_gate_accepts_only_when_every_planned_chapter_is_accepted():
    report = evaluate_book_quality(
        planned_chapter_ids=["chapter_001", "chapter_002"],
        reviews=[
            _review("chapter_001", ChapterReviewDecision.ACCEPT),
            _review("chapter_002", ChapterReviewDecision.ACCEPT),
        ],
    )

    assert report.decision == BookQualityDecision.ACCEPT
    assert report.blocking_chapter_ids == []


def test_book_quality_gate_blocks_missing_or_revise_chapters():
    report = evaluate_book_quality(
        planned_chapter_ids=["chapter_001", "chapter_002"],
        reviews=[_review("chapter_001", ChapterReviewDecision.REVISE)],
    )

    assert report.decision == BookQualityDecision.BLOCK
    assert report.blocking_chapter_ids == ["chapter_001", "chapter_002"]
