from __future__ import annotations

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project


def _proposal():
    return build_book_plan_proposal(
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
                        "target_word_range": {"min_words": 100, "max_words": 500},
                    }
                ],
            }
        )
    )


def test_apply_book_plan_proposal_commits_state_and_auditable_transaction(tmp_path):
    project_path = create_project(tmp_path / "book", title="Book")
    workspace = project_path.parent / "workspace"
    proposal = _proposal()

    result = apply_book_plan_proposal(workspace, proposal)

    reloaded = StateStore.load(workspace / "state")
    journal = workspace / "runs" / ".transactions" / proposal.proposal_id
    assert result.diff_id == "diff_0000"
    assert reloaded.book_plan.chapter("chapter_001").planned_goal == "時刻表の矛盾を発見する。"
    assert reloaded.book_ledger.active_chapter_id == "chapter_001"
    assert (journal / "proposal.yaml").exists()
    assert (journal / "state_diff.yaml").exists()
    assert (journal / "meta.yaml").exists()
