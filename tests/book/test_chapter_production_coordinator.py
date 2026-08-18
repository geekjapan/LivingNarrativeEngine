from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
    open_chapter_review,
    record_chapter_candidate,
    request_chapter_revision,
    start_chapter_production,
)
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.review import ChapterReview, ChapterReviewDecision, ChapterReviewMetrics
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project


def _workspace(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    workspace = project_yaml.parent / "workspace"
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "霧の駅から帰還する。",
                "audience": "mystery readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "異常を知る。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "時刻表の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
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
    assert result.journal_dir.exists()
    assert (workspace / "books" / "chapters" / "chapter_001" / "candidate.md").exists()


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
