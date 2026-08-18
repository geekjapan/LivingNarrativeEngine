from __future__ import annotations

import pytest

from living_narrative.book.planning import (
    StoryBible,
    build_book_plan_proposal,
    proposal_to_state_diff,
)
from living_narrative.state.models import ChapterLifecycle, Visibility


def _story_bible() -> StoryBible:
    return StoryBible.model_validate(
        {
            "premise": "霧の駅で出会った二人が帰還経路を見つける。",
            "audience": "長編ミステリ読者",
            "language": "ja",
            "acts": [
                {
                    "id": "act_001",
                    "promise": "駅に閉じ込められた因果を提示する。",
                    "chapter_ids": ["chapter_001", "chapter_002"],
                }
            ],
            "chapters": [
                {
                    "id": "chapter_001",
                    "act_id": "act_001",
                    "planned_goal": "異常な時刻表を発見する。",
                    "required_thread_ids": ["thread_001"],
                    "character_arc_targets": [
                        {"character_id": "char_001", "delta": "他者への不信を表明する。"}
                    ],
                    "target_word_range": {"min_words": 2500, "max_words": 4500},
                },
                {
                    "id": "chapter_002",
                    "act_id": "act_001",
                    "planned_goal": "時刻表の矛盾を共同で検証する。",
                    "required_thread_ids": ["thread_001"],
                    "character_arc_targets": [
                        {"character_id": "char_001", "delta": "協働を選択する。"}
                    ],
                    "target_word_range": {"min_words": 2500, "max_words": 4500},
                },
            ],
        }
    )


def test_story_bible_produces_deterministic_plan_and_planned_chapter_ledger():
    proposal = build_book_plan_proposal(_story_bible())

    assert proposal.book_plan.premise == "霧の駅で出会った二人が帰還経路を見つける。"
    assert proposal.book_ledger.active_chapter_id == "chapter_001"
    assert [chapter.lifecycle for chapter in proposal.book_ledger.chapters] == [
        ChapterLifecycle.PLANNED,
        ChapterLifecycle.PLANNED,
    ]
    assert proposal.proposal_id == build_book_plan_proposal(_story_bible()).proposal_id


def test_approved_proposal_is_explicitly_represented_as_two_visibility_scoped_state_changes():
    proposal = build_book_plan_proposal(_story_bible())

    diff = proposal_to_state_diff(proposal, turn=4)

    assert diff.turn == 4
    assert [(change.target, change.op, change.visibility) for change in diff.changes] == [
        ("book_plan", "set", Visibility.CANON),
        ("book_ledger", "set", Visibility.GM_ONLY),
    ]
    assert diff.changes[0].value["chapters"][0]["id"] == "chapter_001"


def test_story_bible_rejects_empty_authorial_intent():
    raw = _story_bible().model_dump(mode="json")
    raw["premise"] = "  "

    with pytest.raises(ValueError, match="premise must not be blank"):
        StoryBible.model_validate(raw)
