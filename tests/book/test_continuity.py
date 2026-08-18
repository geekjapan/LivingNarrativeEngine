from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.continuity import advance_continuity_ledger, render_continuity_digest
from living_narrative.state.models import BookLedgerState


def test_continuity_ledger_keeps_reader_safe_bounded_digest_and_open_threads():
    ledger = BookLedgerState()
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="---\nchapter_id: chapter_001\n---\n\n# chapter_001\n\n" + "公開本文。" * 500,
    )

    updated = advance_continuity_ledger(
        ledger,
        candidate,
        required_thread_ids=["thread_001", "thread_002"],
        covered_thread_ids=["thread_001"],
        max_summary_chars=120,
    )

    assert ledger.continuity.entries == []
    assert updated.continuity.entries[0].chapter_id == "chapter_001"
    assert len(updated.continuity.entries[0].summary) <= 120
    assert updated.continuity.open_thread_ids == ["thread_002"]
    digest = render_continuity_digest(updated.continuity, max_chars=100)
    assert digest == updated.continuity.entries[0].summary[:100]


def test_continuity_ledger_closes_threads_covered_by_a_later_chapter():
    first = advance_continuity_ledger(
        BookLedgerState(),
        ChapterCandidate(
            chapter_id="chapter_001",
            source_turns=[1],
            markdown="# chapter_001\n\n公開本文。",
        ),
        required_thread_ids=["thread_001", "thread_002"],
        covered_thread_ids=["thread_001"],
    )
    later = advance_continuity_ledger(
        first,
        ChapterCandidate(
            chapter_id="chapter_002",
            source_turns=[2],
            markdown="# chapter_002\n\n回収本文。",
        ),
        required_thread_ids=["thread_002"],
        covered_thread_ids=["thread_002"],
    )

    assert first.continuity.open_thread_ids == ["thread_002"]
    assert later.continuity.open_thread_ids == []
    assert later.continuity.entries[-1].open_thread_ids == []
