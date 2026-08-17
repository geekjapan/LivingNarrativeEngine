from __future__ import annotations

from living_narrative.book.artifacts import load_chapter_artifacts, save_chapter_artifacts
from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.review import (
    ChapterReview,
    ChapterReviewDecision,
    ChapterReviewMetrics,
)


def test_chapter_artifacts_round_trip_with_separate_candidate_and_review(tmp_path):
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1, 2],
        markdown="# chapter_001\n\n澪は時刻表を読んだ。\n",
    )
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=12, min_units=10, max_units=100),
    )

    artifact_dir = save_chapter_artifacts(tmp_path, candidate, review)
    loaded_candidate, loaded_review = load_chapter_artifacts(tmp_path, "chapter_001")

    assert artifact_dir == tmp_path / "chapter_001"
    assert (artifact_dir / "candidate.md").read_text(encoding="utf-8") == candidate.markdown
    assert (artifact_dir / "review.yaml").exists()
    assert loaded_candidate == candidate
    assert loaded_review == review
