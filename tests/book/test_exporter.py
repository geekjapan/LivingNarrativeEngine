from __future__ import annotations

import pytest

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
    open_chapter_review,
    record_chapter_candidate,
    start_chapter_production,
)
from living_narrative.book.exporter import IncompleteManuscriptError, export_accepted_manuscript
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.review import ChapterReview, ChapterReviewDecision, ChapterReviewMetrics
from living_narrative.workspace.init import create_project


def _workspace(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "帳簿を調べる。",
                "audience": "fantasy readers",
                "acts": [{"id": "act_001", "promise": "調査", "chapter_ids": ["chapter_001"]}],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "矛盾を見つける。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml.parent / "workspace"


def test_exporter_writes_only_accepted_attempt_body_and_reproducible_manifest(tmp_path):
    workspace = _workspace(tmp_path)
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter_001\n\n公開本文。\n",
    )
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )
    start_chapter_production(workspace, "chapter_001")
    record_chapter_candidate(workspace, candidate, review)
    open_chapter_review(workspace, "chapter_001")
    accept_chapter_review(workspace, "chapter_001")

    result = export_accepted_manuscript(workspace, tmp_path / "exports")

    assert result.manuscript_path.read_text(encoding="utf-8") == "# chapter_001\n\n公開本文。\n"
    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert "attempt_001" in manifest
    assert "review" not in manifest
    assert "/" not in manifest


def test_exporter_rejects_book_with_unaccepted_chapter(tmp_path):
    workspace = _workspace(tmp_path)

    with pytest.raises(IncompleteManuscriptError, match="not accepted"):
        export_accepted_manuscript(workspace, tmp_path / "exports")
