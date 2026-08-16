from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate, ChapterContext
from living_narrative.book.review import ChapterReviewDecision, review_chapter


def _context(min_words: int = 5) -> ChapterContext:
    return ChapterContext(
        chapter_id="chapter_001",
        act_id="act_001",
        planned_goal="時刻表の矛盾を発見する。",
        target_min_words=min_words,
        target_max_words=100,
    )


def test_chapter_review_requests_revision_when_body_is_below_minimum_length():
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter\n\n短い。",
    )

    review = review_chapter(_context(min_words=10), candidate)

    assert review.decision == ChapterReviewDecision.REVISE
    assert review.metrics.body_units < 10
    assert "below minimum" in review.reasons[0]


def test_chapter_review_accepts_candidate_inside_deterministic_length_gate():
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter\n\n時刻表の矛盾を澪は見つけ、駅員に問いただした。",
    )

    review = review_chapter(_context(min_words=5), candidate)

    assert review.decision == ChapterReviewDecision.ACCEPT
    assert review.metrics.body_units >= 5
    assert review.reasons == []
