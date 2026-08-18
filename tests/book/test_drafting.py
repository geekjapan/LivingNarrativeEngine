from __future__ import annotations

import pytest

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.drafting import ChapterDraftResponse, run_chapter_draft
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.workspace.init import create_project


class _Gateway:
    def __init__(self, body: str = "灰の書庫で、透は帳簿の矛盾を見つけた。") -> None:
        self.body = body
        self.call_count = 0

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.call_count += 1
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
