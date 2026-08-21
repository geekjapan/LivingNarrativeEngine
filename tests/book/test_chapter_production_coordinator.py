from __future__ import annotations

import pytest

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
    open_chapter_review,
    record_chapter_candidate,
    request_chapter_revision,
    start_chapter_production,
)
from living_narrative.book.lineage import load_chapter_lineage, record_chapter_attempt
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.review import (
    ChapterReview,
    ChapterReviewDecision,
    ChapterReviewMetrics,
    SemanticContinuityAssessment,
    SemanticContinuityFinding,
)
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project


def _story_bible(*chapter_goals: str):
    chapters = [
        {
            "id": f"chapter_{index:03d}",
            "act_id": "act_001",
            "planned_goal": goal,
            "target_word_range": {"min_words": 10, "max_words": 100},
        }
        for index, goal in enumerate(chapter_goals, start=1)
    ]
    return StoryBible.model_validate(
        {
            "premise": "霧の駅から帰還する。",
            "audience": "mystery readers",
            "acts": [
                {
                    "id": "act_001",
                    "promise": "異常を知る。",
                    "chapter_ids": [chapter["id"] for chapter in chapters],
                }
            ],
            "chapters": chapters,
        }
    )


def _workspace(tmp_path, *chapter_goals: str):
    project_yaml = create_project(tmp_path / "book", title="Book")
    workspace = project_yaml.parent / "workspace"
    proposal = build_book_plan_proposal(
        _story_bible(*(chapter_goals or ("時刻表の矛盾を発見する。",)))
    )
    apply_book_plan_proposal(workspace, proposal)
    return workspace


def test_chapter_production_lifecycle_persists_candidate_review_and_acceptance(tmp_path):
    workspace = _workspace(tmp_path)
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1, 2],
        markdown="# chapter_001\n\n澪は時刻表の矛盾を見つけた。\n",
    )
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )

    start_chapter_production(workspace, "chapter_001")
    record_chapter_candidate(workspace, candidate, review)
    open_chapter_review(workspace, "chapter_001")
    result = accept_chapter_review(workspace, "chapter_001")

    bundle = StateStore.load(workspace / "state")
    assert bundle.book_ledger.chapter("chapter_001").lifecycle == ChapterLifecycle.ACCEPTED
    assert bundle.book_ledger.chapter("chapter_001").review_decision == "accept"
    assert bundle.book_ledger.continuity.entries[0].chapter_id == "chapter_001"
    assert bundle.book_ledger.continuity.act_summaries[0].act_id == "act_001"
    assert result.journal_dir.exists()
    assert (workspace / "books" / "chapters" / "chapter_001" / "candidate.md").exists()
    lineage = load_chapter_lineage(workspace / "books" / "chapters", "chapter_001")
    assert lineage.accepted_attempt_id == "attempt_001"


def test_semantic_block_review_cannot_be_accepted(tmp_path):
    workspace = _workspace(tmp_path)
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter_001\n\n澪は時刻表の矛盾を見つけた。\n",
    )
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.REVISE,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
        semantic=SemanticContinuityAssessment(
            findings=[
                SemanticContinuityFinding(
                    code="required_thread_missing",
                    severity="block",
                    evidence="required thread thread_001 is not covered",
                    repair_instruction="Address thread_001.",
                )
            ]
        ),
    )

    start_chapter_production(workspace, "chapter_001")
    record_chapter_candidate(workspace, candidate, review)
    open_chapter_review(workspace, "chapter_001")

    with pytest.raises(ValueError, match="cannot accept a non-accept review"):
        accept_chapter_review(workspace, "chapter_001")

    assert StateStore.load(workspace / "state").book_ledger.chapter("chapter_001").lifecycle == (
        ChapterLifecycle.REVIEW
    )


def test_revised_candidate_uses_a_new_transaction_and_replaces_current_artifact(tmp_path):
    workspace = _workspace(tmp_path)
    first = ChapterCandidate(chapter_id="chapter_001", source_turns=[1], markdown="# first\n")
    revised = ChapterCandidate(chapter_id="chapter_001", source_turns=[2], markdown="# revised\n")
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )

    start_chapter_production(workspace, "chapter_001")
    first_result = record_chapter_candidate(workspace, first, review)
    open_chapter_review(workspace, "chapter_001")
    request_chapter_revision(workspace, "chapter_001")
    revised_result = record_chapter_candidate(workspace, revised, review)

    assert revised_result.journal_dir != first_result.journal_dir
    assert (
        StateStore.load(workspace / "state").book_ledger.chapter("chapter_001").lifecycle
        == ChapterLifecycle.CANDIDATE
    )
    artifact = workspace / "books" / "chapters" / "chapter_001" / "candidate.md"
    assert artifact.read_text(encoding="utf-8") == revised.markdown


def test_start_rejects_second_chapter_while_another_is_in_production(tmp_path):
    workspace = _workspace(tmp_path, "時刻表の矛盾を発見する。", "改札の記録を照合する。")

    first = start_chapter_production(workspace, "chapter_001")
    with pytest.raises(ValueError, match="chapter_001 is already in production"):
        start_chapter_production(workspace, "chapter_002")

    repeated = start_chapter_production(workspace, "chapter_001")
    assert repeated.journal_dir == first.journal_dir
    assert (
        StateStore.load(workspace / "state").book_ledger.chapter("chapter_002").lifecycle
        == ChapterLifecycle.PLANNED
    )


def test_replacement_plan_uses_a_new_running_journal_for_reused_chapter_id(tmp_path):
    workspace = _workspace(tmp_path, "時刻表の矛盾を発見する。")
    first = start_chapter_production(workspace, "chapter_001")

    apply_book_plan_proposal(
        workspace, build_book_plan_proposal(_story_bible("改札の記録を照合する。"))
    )
    replaced = start_chapter_production(workspace, "chapter_001")

    assert replaced.journal_dir != first.journal_dir
    assert replaced.journal_dir.exists()
    assert (
        StateStore.load(workspace / "state").book_ledger.chapter("chapter_001").lifecycle
        == ChapterLifecycle.RUNNING
    )


def test_acceptance_selects_the_attempt_matching_the_reviewed_candidate(tmp_path):
    """List position is not evidence of what the author reviewed: a lineage can gain a newer
    attempt while an older candidate is still the one on the review desk."""
    workspace = _workspace(tmp_path)
    reviewed = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter_001\n\n澪は時刻表の矛盾を見つけた。\n",
    )
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )
    start_chapter_production(workspace, "chapter_001")
    record_chapter_candidate(
        workspace, reviewed, review, draft_run_id="chapter_chapter_001_attempt_001"
    )
    open_chapter_review(workspace, "chapter_001")

    chapters_root = workspace / "books" / "chapters"
    record_chapter_attempt(
        chapters_root,
        ChapterCandidate(
            chapter_id="chapter_001",
            source_turns=[2],
            markdown="# chapter_001\n\n駅長は最終列車の記録を否定した。\n",
        ),
        review,
    )

    accept_chapter_review(workspace, "chapter_001")

    lineage = load_chapter_lineage(chapters_root, "chapter_001")
    accepted = next(item for item in lineage.attempts if item.id == lineage.accepted_attempt_id)
    assert accepted.candidate_markdown == reviewed.markdown
    assert accepted.draft_run_id == "chapter_chapter_001_attempt_001"
    # The continuity ledger must summarise the same attempt the author reviewed.
    entry = StateStore.load(workspace / "state").book_ledger.continuity.entries[-1]
    assert "澪は時刻表の矛盾を見つけた。" in entry.summary
