from __future__ import annotations

import pytest

from living_narrative.book.budget import BookBudgetPolicy, BudgetExceededError
from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.drafting import run_chapter_draft
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.workspace.init import create_project


class _Gateway:
    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.call_count += 1
        return response_schema(body="公開本文")


def _project(tmp_path):
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
    return project_yaml


def test_budget_blocks_chapter_attempt_before_provider_call_and_records_reason(tmp_path):
    project_yaml = _project(tmp_path)
    gateway = _Gateway()

    with pytest.raises(BudgetExceededError, match="chapter attempt budget"):
        run_chapter_draft(
            project_yaml,
            "chapter_001",
            attempt=2,
            gateway=gateway,
            budget=BookBudgetPolicy(max_attempts_per_chapter=1),
        )

    run_dir = (
        project_yaml.parent
        / "workspace"
        / "runs"
        / "chapter_drafts"
        / "chapter_chapter_001_attempt_002"
    )
    assert gateway.call_count == 0
    assert (run_dir / "circuit_breaker.yaml").exists()


def test_budget_blocks_book_attempts_across_chapters_before_provider_call(tmp_path):
    project_yaml = _project(tmp_path)
    gateway = _Gateway()
    budget = BookBudgetPolicy(max_attempts_per_book=1)

    run_chapter_draft(project_yaml, "chapter_001", gateway=gateway, budget=budget)

    with pytest.raises(BudgetExceededError, match="book attempt budget"):
        run_chapter_draft(project_yaml, "chapter_001", attempt=2, gateway=gateway, budget=budget)

    assert gateway.call_count == 1
