from __future__ import annotations

import pytest

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.lineage import (
    accept_chapter_attempt,
    load_chapter_lineage,
    record_chapter_attempt,
)
from living_narrative.book.review import ChapterReview, ChapterReviewDecision, ChapterReviewMetrics


def _review(decision: ChapterReviewDecision) -> ChapterReview:
    return ChapterReview(
        chapter_id="chapter_001",
        decision=decision,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )


def test_attempt_lineage_preserves_immutable_revisions_and_accepted_pointer(tmp_path):
    chapters_root = tmp_path / "chapters"
    first = record_chapter_attempt(
        chapters_root,
        ChapterCandidate(chapter_id="chapter_001", source_turns=[1], markdown="# first\n"),
        _review(ChapterReviewDecision.REVISE),
        draft_run_id="chapter_chapter_001_attempt_001",
    )
    revised = record_chapter_attempt(
        chapters_root,
        ChapterCandidate(chapter_id="chapter_001", source_turns=[2], markdown="# revised\n"),
        _review(ChapterReviewDecision.ACCEPT),
        draft_run_id="chapter_chapter_001_attempt_002",
    )

    accepted = accept_chapter_attempt(chapters_root, "chapter_001", revised.id)
    lineage = load_chapter_lineage(chapters_root, "chapter_001")

    assert first.id == "attempt_001"
    assert revised.id == "attempt_002"
    assert revised.parent_attempt_id == first.id
    assert lineage.attempts[0].candidate_markdown == "# first\n"
    assert lineage.attempts[1].candidate_markdown == "# revised\n"
    assert accepted.accepted_attempt_id == revised.id
    with pytest.raises(FileExistsError):
        record_chapter_attempt(
            chapters_root,
            ChapterCandidate(chapter_id="chapter_001", source_turns=[3], markdown="# revised\n"),
            _review(ChapterReviewDecision.ACCEPT),
        )
