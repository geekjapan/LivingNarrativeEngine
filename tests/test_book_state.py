from __future__ import annotations

import pytest

from living_narrative.state.diff import StateDiff, StateDiffChange, apply_state_diff, rollback
from living_narrative.state.models import (
    BookChapterLedger,
    BookLedgerState,
    BookPlanState,
    ChapterLifecycle,
    Visibility,
)
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import commit_state_diff
from living_narrative.workspace.init import create_project


def _book_plan_value() -> dict[str, object]:
    return {
        "premise": "霧の駅から帰還する二人の因果を描く。",
        "audience": "長編ミステリ読者",
        "language": "ja",
        "acts": [
            {
                "id": "act_001",
                "promise": "帰還不能の理由を発見する。",
                "chapter_ids": ["chapter_001"],
            }
        ],
        "chapters": [
            {
                "id": "chapter_001",
                "act_id": "act_001",
                "planned_goal": "最初の手掛かりを読者に提示する。",
                "required_thread_ids": ["thread_001"],
                "character_arc_targets": [
                    {"character_id": "char_001", "delta": "孤立から協働へ移る。"}
                ],
                "target_word_range": {"min_words": 2500, "max_words": 4500},
            }
        ],
    }


def test_book_plan_validates_act_chapter_membership_and_unique_ids():
    plan = BookPlanState.model_validate(_book_plan_value())

    assert plan.chapter("chapter_001").planned_goal == "最初の手掛かりを読者に提示する。"
    assert plan.acts[0].chapter_ids == ["chapter_001"]

    duplicate_chapter = _book_plan_value()
    duplicate_chapter["chapters"] = [
        *duplicate_chapter["chapters"],
        duplicate_chapter["chapters"][0],
    ]
    with pytest.raises(ValueError, match="chapter ids must be unique"):
        BookPlanState.model_validate(duplicate_chapter)

    unlisted_chapter = _book_plan_value()
    unlisted_chapter["acts"][0]["chapter_ids"] = []
    with pytest.raises(ValueError, match="must be listed by exactly one act"):
        BookPlanState.model_validate(unlisted_chapter)


def test_book_ledger_rejects_illegal_lifecycle_transition_without_mutating_source():
    ledger = BookLedgerState(
        active_chapter_id="chapter_001",
        chapters=[BookChapterLedger(id="chapter_001", lifecycle=ChapterLifecycle.PLANNED)],
    )

    running = ledger.transition("chapter_001", ChapterLifecycle.RUNNING)
    assert ledger.chapter("chapter_001").lifecycle == ChapterLifecycle.PLANNED
    assert running.chapter("chapter_001").lifecycle == ChapterLifecycle.RUNNING

    with pytest.raises(ValueError, match="not allowed"):
        ledger.transition("chapter_001", ChapterLifecycle.ACCEPTED)


def test_book_state_is_updated_and_rolled_back_only_through_state_diff(tmp_path):
    project_path = create_project(
        tmp_path / "book-state", title="Book state", template="mist_station"
    )
    bundle = StateStore.load(project_path.parent / "workspace" / "state")
    assert bundle.book_plan == BookPlanState()
    assert bundle.book_ledger == BookLedgerState()

    ledger_value = {
        "active_chapter_id": "chapter_001",
        "chapters": [{"id": "chapter_001", "lifecycle": "planned"}],
    }
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="book_plan",
                op="set",
                value=_book_plan_value(),
                visibility=Visibility.CANON,
            ),
            StateDiffChange(
                target="book_ledger",
                op="set",
                value=ledger_value,
                visibility=Visibility.GM_ONLY,
            ),
        ],
    )

    applied = apply_state_diff(bundle, diff)

    assert applied.bundle.book_plan.chapter("chapter_001").target_word_range.min_words == 2500
    assert applied.bundle.book_ledger.active_chapter_id == "chapter_001"
    restored = rollback(applied.bundle, [applied.inverse_diff])
    assert restored.book_plan == BookPlanState()
    assert restored.book_ledger == BookLedgerState()


def test_book_state_is_persisted_by_transaction_and_materializes_state_files(tmp_path):
    project_path = create_project(tmp_path / "book-transaction", title="Book transaction")
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="book_plan",
                op="set",
                value=_book_plan_value(),
                visibility=Visibility.CANON,
            )
        ],
    )

    commit_state_diff(StateStore.load(state_dir), diff, state_dir, turn_dir)

    reloaded = StateStore.load(state_dir)
    assert reloaded.book_plan.chapter("chapter_001").act_id == "act_001"
    assert (state_dir / "book_plan.yaml").exists()
    assert (state_dir / "book_ledger.yaml").exists()
    assert (turn_dir / "commit_intent.yaml").exists()
