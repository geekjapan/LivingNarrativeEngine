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
    # Re-recording the identical candidate/review/provenance tuple is refused; a differing
    # review or draft run is a genuinely new attempt (see the dedicated test below).
    with pytest.raises(FileExistsError):
        record_chapter_attempt(
            chapters_root,
            ChapterCandidate(chapter_id="chapter_001", source_turns=[3], markdown="# revised\n"),
            _review(ChapterReviewDecision.ACCEPT),
            draft_run_id="chapter_chapter_001_attempt_002",
        )


def test_retry_completes_an_orphaned_attempt_directory(tmp_path):
    """A crash between writing the attempt files and replacing lineage.yaml leaves a directory
    the manifest never recorded; the retry must finish it rather than block the chapter."""
    chapters_root = tmp_path / "chapters"
    orphan = chapters_root / "chapter_001" / "attempts" / "attempt_001"
    orphan.mkdir(parents=True)
    (orphan / "candidate.md").write_text("# partial\n", encoding="utf-8")

    attempt = record_chapter_attempt(
        chapters_root,
        ChapterCandidate(chapter_id="chapter_001", source_turns=[1], markdown="# retried\n"),
        _review(ChapterReviewDecision.ACCEPT),
    )

    assert attempt.id == "attempt_001"
    assert (orphan / "candidate.md").read_text(encoding="utf-8") == "# retried\n"
    assert load_chapter_lineage(chapters_root, "chapter_001").attempts[0].id == "attempt_001"


def test_same_body_under_a_new_review_is_a_new_attempt(tmp_path):
    """Attempt identity is candidate + review + provenance: a replacement plan re-drafting the
    same body under a new review must not inherit the previous decision."""
    chapters_root = tmp_path / "chapters"
    candidate = ChapterCandidate(
        chapter_id="chapter_001", source_turns=[1], markdown="# same body\n"
    )
    first = record_chapter_attempt(chapters_root, candidate, _review(ChapterReviewDecision.REVISE))

    second = record_chapter_attempt(
        chapters_root, candidate, _review(ChapterReviewDecision.ACCEPT), draft_run_id="run_002"
    )

    assert second.id != first.id
    assert second.review.decision is ChapterReviewDecision.ACCEPT
    with pytest.raises(FileExistsError, match="identical attempt"):
        record_chapter_attempt(
            chapters_root, candidate, _review(ChapterReviewDecision.ACCEPT), draft_run_id="run_002"
        )
