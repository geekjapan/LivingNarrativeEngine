from __future__ import annotations

from living_narrative.book.scheduler import NextChapterAction, schedule_next_chapter
from living_narrative.state.models import (
    BookChapterLedger,
    BookLedgerState,
    ChapterLifecycle,
)


def test_scheduler_selects_first_planned_chapter_when_none_is_active():
    decision = schedule_next_chapter(
        BookLedgerState(
            chapters=[
                BookChapterLedger(id="chapter_001", lifecycle=ChapterLifecycle.PLANNED),
                BookChapterLedger(id="chapter_002", lifecycle=ChapterLifecycle.PLANNED),
            ]
        )
    )

    assert decision.action == NextChapterAction.START
    assert decision.chapter_id == "chapter_001"


def test_scheduler_requests_revision_before_starting_later_chapters():
    decision = schedule_next_chapter(
        BookLedgerState(
            active_chapter_id="chapter_001",
            chapters=[
                BookChapterLedger(id="chapter_001", lifecycle=ChapterLifecycle.REVISING),
                BookChapterLedger(id="chapter_002", lifecycle=ChapterLifecycle.PLANNED),
            ],
        )
    )

    assert decision.action == NextChapterAction.REVISE
    assert decision.chapter_id == "chapter_001"


def test_scheduler_waits_when_a_chapter_is_already_in_production():
    decision = schedule_next_chapter(
        BookLedgerState(
            active_chapter_id="chapter_001",
            chapters=[
                BookChapterLedger(id="chapter_001", lifecycle=ChapterLifecycle.RUNNING),
                BookChapterLedger(id="chapter_002", lifecycle=ChapterLifecycle.PLANNED),
            ],
        )
    )

    assert decision.action == NextChapterAction.WAIT_FOR_REVIEW
    assert decision.chapter_id is None
