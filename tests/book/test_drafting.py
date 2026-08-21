from __future__ import annotations

import pytest
import yaml

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
    open_chapter_review,
    record_chapter_candidate,
    start_chapter_production,
)
from living_narrative.book.drafting import ChapterDraftResponse, run_chapter_draft
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.review import ChapterReview, ChapterReviewDecision, ChapterReviewMetrics
from living_narrative.state.transaction import ProjectLockError, project_lock
from living_narrative.workspace.init import create_project


class _Gateway:
    def __init__(self, body: str = "灰の書庫で、透は帳簿の矛盾を見つけた。") -> None:
        self.body = body
        self.call_count = 0
        self.messages: list[dict] = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.call_count += 1
        self.messages = messages
        return response_schema(body=self.body)


def _project(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "書庫から王国の飢饉を調べる。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "帳簿の矛盾を発見する。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "飢饉帳簿の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml


def test_draft_run_persists_prompt_response_and_reuses_completed_result(tmp_path):
    project_yaml = _project(tmp_path)
    gateway = _Gateway()

    first = run_chapter_draft(project_yaml, "chapter_001", gateway=gateway)
    second = run_chapter_draft(project_yaml, "chapter_001", gateway=gateway)

    assert first.response.body == gateway.body
    assert second.run_id == first.run_id
    assert gateway.call_count == 1
    assert (first.run_dir / "request.yaml").exists()
    assert (first.run_dir / "prompt.yaml").exists()
    assert (first.run_dir / "response.yaml").exists()
    assert (first.run_dir / "meta.yaml").exists()


def test_draft_prompt_includes_current_act_continuity_from_prior_accepted_chapter(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    workspace = project_yaml.parent / "workspace"
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "書庫から王国の飢饉を調べる。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "帳簿の矛盾を発見する。",
                        "chapter_ids": ["chapter_001", "chapter_002"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "飢饉帳簿の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    },
                    {
                        "id": "chapter_002",
                        "act_id": "act_001",
                        "planned_goal": "逆向きの時計の意味を調べる。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    },
                ],
            }
        )
    )
    apply_book_plan_proposal(workspace, proposal)
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[],
        markdown="# chapter_001\n\n透は逆向きの時計と帳簿の矛盾を結びつけた。\n",
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
    gateway = _Gateway()

    run_chapter_draft(project_yaml, "chapter_002", gateway=gateway)

    prompt = gateway.messages[1]["content"]
    assert "Hierarchical continuity:" in prompt
    assert "Act act_001:" in prompt
    assert "逆向きの時計" in prompt


def test_draft_run_keeps_partial_artifact_and_can_resume_after_provider_failure(tmp_path):
    project_yaml = _project(tmp_path)

    class FailingGateway:
        def complete(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        run_chapter_draft(project_yaml, "chapter_001", gateway=FailingGateway())

    recovered = run_chapter_draft(project_yaml, "chapter_001", gateway=_Gateway("改稿本文"))

    assert recovered.response == ChapterDraftResponse(body="改稿本文")
    assert (recovered.run_dir / "request.yaml").exists()
    assert (recovered.run_dir / "meta.yaml").exists()


def test_draft_run_contends_for_workspace_lock_used_by_chapter_commits(tmp_path):
    project_yaml = _project(tmp_path)
    workspace_root = project_yaml.parent / "workspace"

    with project_lock(workspace_root):
        with pytest.raises(ProjectLockError):
            run_chapter_draft(project_yaml, "chapter_001", gateway=_Gateway())


def test_replacement_plan_does_not_resume_the_previous_plan_response(tmp_path):
    """A reused chapter ID and attempt number must not hand the new goal prose written for the
    old one: the run identity carries the plan generation."""
    project_yaml = _project(tmp_path)
    first = run_chapter_draft(project_yaml, "chapter_001", gateway=_Gateway("旧計画の本文。"))

    apply_book_plan_proposal(
        project_yaml.parent / "workspace",
        build_book_plan_proposal(
            StoryBible.model_validate(
                {
                    "premise": "書庫から王国の飢饉を調べる。",
                    "audience": "fantasy readers",
                    "acts": [
                        {
                            "id": "act_001",
                            "promise": "帳簿の矛盾を発見する。",
                            "chapter_ids": ["chapter_001"],
                        }
                    ],
                    "chapters": [
                        {
                            "id": "chapter_001",
                            "act_id": "act_001",
                            "planned_goal": "王都の飢饉報告を突き合わせる。",
                            "target_word_range": {"min_words": 20, "max_words": 200},
                        }
                    ],
                }
            )
        ),
    )
    replacement = _Gateway("新計画の本文。")

    second = run_chapter_draft(project_yaml, "chapter_001", gateway=replacement)

    assert second.run_id != first.run_id
    assert second.response.body == "新計画の本文。"
    assert replacement.call_count == 1


def test_failed_retry_keeps_the_original_request_and_prompt(tmp_path):
    """One run ID must cover one set of inputs: a retry resumes the persisted request instead of
    rebuilding it from whatever the world looks like now."""
    project_yaml = _project(tmp_path)

    class FailingGateway:
        call_count = 0

        def complete(self, binding_key, messages, response_schema, prompt_template_name):
            type(self).call_count += 1
            raise RuntimeError("provider down")

    with pytest.raises(RuntimeError):
        run_chapter_draft(project_yaml, "chapter_001", gateway=FailingGateway())
    runs = list((project_yaml.parent / "workspace" / "runs" / "chapter_drafts").iterdir())
    assert len(runs) == 1
    original = (runs[0] / "request.yaml").read_text(encoding="utf-8")

    state_dir = project_yaml.parent / "workspace" / "state"
    world = yaml.safe_load((state_dir / "world.yaml").read_text(encoding="utf-8"))
    world["summary"] = "書庫の空気が変わった。"
    (state_dir / "world.yaml").write_text(
        yaml.safe_dump(world, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    run_chapter_draft(project_yaml, "chapter_001", gateway=_Gateway())

    assert (runs[0] / "request.yaml").read_text(encoding="utf-8") == original
