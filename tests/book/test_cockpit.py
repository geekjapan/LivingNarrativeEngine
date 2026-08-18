from __future__ import annotations

from living_narrative.book.cockpit import build_book_cockpit
from living_narrative.state.models import (
    BookActPlan,
    BookChapterLedger,
    BookChapterPlan,
    BookLedgerState,
    BookPlanState,
    BookWordRange,
    ChapterLifecycle,
    WorldState,
    WorldStateBundle,
)


def test_cockpit_projects_chapter_status_and_next_action_without_world_secrets():
    bundle = WorldStateBundle(
        world=WorldState(id="world_001", name="霧の駅", summary="station"),
        book_plan=BookPlanState(
            premise="帰還経路を探す。",
            audience="mystery readers",
            acts=[BookActPlan(id="act_001", promise="異常を知る", chapter_ids=["chapter_001"])],
            chapters=[
                BookChapterPlan(
                    id="chapter_001",
                    act_id="act_001",
                    planned_goal="時刻表の矛盾を発見する。",
                    target_word_range=BookWordRange(min_words=100, max_words=500),
                )
            ],
        ),
        book_ledger=BookLedgerState(
            active_chapter_id="chapter_001",
            chapters=[BookChapterLedger(id="chapter_001", lifecycle=ChapterLifecycle.REVISING)],
        ),
    )

    cockpit = build_book_cockpit(bundle)

    assert cockpit.next_action == "revise"
    assert cockpit.chapters[0].chapter_id == "chapter_001"
    assert cockpit.chapters[0].lifecycle == ChapterLifecycle.REVISING
    assert cockpit.chapters[0].target_min_words == 100
    assert cockpit.chapters[0].target_max_words == 500
    assert cockpit.chapters[0].startable is False
    dumped = cockpit.model_dump(mode="json")
    assert dumped["chapters"][0]["chapter_id"] == "chapter_001"
    assert "id" not in dumped["chapters"][0]
    assert "secrets" not in cockpit.model_dump_json()


def test_cockpit_hides_start_actions_from_non_authoring_sessions():
    """The UI must not offer controls whose only outcome is the API's 403."""
    bundle = WorldStateBundle(
        world=WorldState(id="world_001", name="霧の駅", summary="station"),
        book_plan=BookPlanState(
            premise="帰還経路を探す。",
            audience="mystery readers",
            acts=[BookActPlan(id="act_001", promise="異常を知る", chapter_ids=["chapter_001"])],
            chapters=[
                BookChapterPlan(
                    id="chapter_001",
                    act_id="act_001",
                    planned_goal="時刻表の矛盾を発見する。",
                    target_word_range=BookWordRange(min_words=100, max_words=500),
                )
            ],
        ),
        book_ledger=BookLedgerState(
            chapters=[BookChapterLedger(id="chapter_001", lifecycle=ChapterLifecycle.PLANNED)],
        ),
    )

    observer = build_book_cockpit(bundle)
    author = build_book_cockpit(bundle, can_operate=True)

    assert observer.can_operate is False
    assert observer.chapters[0].startable is False
    assert author.can_operate is True
    assert author.chapters[0].startable is True
