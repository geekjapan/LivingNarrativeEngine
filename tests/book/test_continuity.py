from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.continuity import (
    advance_continuity_ledger,
    render_continuity_digest,
    render_hierarchical_continuity_context,
)
from living_narrative.state.models import BookLedgerState, CharacterArcTarget


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


def test_continuity_ledger_derives_act_and_character_arc_summaries_from_accepted_chapter():
    updated = advance_continuity_ledger(
        BookLedgerState(),
        ChapterCandidate(
            chapter_id="chapter_001",
            source_turns=[1],
            markdown="# chapter_001\n\n透は帳簿の不正を疑う勇気を得た。",
        ),
        required_thread_ids=["thread_001"],
        covered_thread_ids=["thread_001"],
        act_id="act_001",
        character_arc_targets=[
            CharacterArcTarget(character_id="char_001", delta="帳簿の不正を疑う勇気を得る。")
        ],
        covered_character_arc_target_ids=["char_001"],
    )

    act_summary = updated.continuity.act_summaries[0]
    character_arc = updated.continuity.character_arcs[0]
    projection = render_hierarchical_continuity_context(
        updated.continuity,
        act_id="act_001",
        character_ids=["char_001"],
    )

    assert act_summary.act_id == "act_001"
    assert act_summary.chapter_ids == ["chapter_001"]
    assert "透は帳簿の不正を疑う勇気を得た。" in act_summary.summary
    assert character_arc.character_id == "char_001"
    assert character_arc.observed_deltas == ["帳簿の不正を疑う勇気を得る。"]
    assert "Act act_001:" in projection
    assert "Character char_001:" in projection


def test_continuity_ledger_accumulates_act_summary_across_accepted_chapters():
    first = advance_continuity_ledger(
        BookLedgerState(),
        ChapterCandidate(
            chapter_id="chapter_001",
            source_turns=[1],
            markdown="# chapter_001\n\n透は鐘の異常を観察した。",
        ),
        required_thread_ids=[],
        covered_thread_ids=[],
        act_id="act_001",
    )
    later = advance_continuity_ledger(
        first,
        ChapterCandidate(
            chapter_id="chapter_002",
            source_turns=[2],
            markdown="# chapter_002\n\n透は帳簿の余白に同じ印を見つけた。",
        ),
        required_thread_ids=[],
        covered_thread_ids=[],
        act_id="act_001",
    )

    act_summary = later.continuity.act_summaries[0]
    assert act_summary.chapter_ids == ["chapter_001", "chapter_002"]
    assert "鐘の異常" in act_summary.summary
    assert "帳簿の余白" in act_summary.summary


def test_continuity_ledger_accumulates_multiple_covered_character_arc_deltas():
    first = advance_continuity_ledger(
        BookLedgerState(),
        ChapterCandidate(
            chapter_id="chapter_001",
            source_turns=[1],
            markdown="# chapter_001\n\n透は帳簿の不正を疑う勇気を得た。",
        ),
        required_thread_ids=[],
        covered_thread_ids=[],
        character_arc_targets=[
            CharacterArcTarget(character_id="char_001", delta="帳簿の不正を疑う勇気を得る。")
        ],
        covered_character_arc_target_ids=["char_001"],
    )
    later = advance_continuity_ledger(
        first,
        ChapterCandidate(
            chapter_id="chapter_002",
            source_turns=[2],
            markdown="# chapter_002\n\n透は疑いを仲間に告げる決意をした。",
        ),
        required_thread_ids=[],
        covered_thread_ids=[],
        character_arc_targets=[
            CharacterArcTarget(character_id="char_001", delta="疑いを仲間に告げる決意をする。")
        ],
        covered_character_arc_target_ids=["char_001"],
    )

    character_arc = later.continuity.character_arcs[0]
    assert character_arc.chapter_ids == ["chapter_001", "chapter_002"]
    assert character_arc.observed_deltas == [
        "帳簿の不正を疑う勇気を得る。",
        "疑いを仲間に告げる決意をする。",
    ]


def test_continuity_ledger_advances_legacy_state_without_hierarchical_fields():
    legacy_ledger = BookLedgerState.model_validate(
        {
            "continuity": {
                "entries": [
                    {
                        "chapter_id": "chapter_001",
                        "summary": "透は鐘の異常を観察した。",
                        "open_thread_ids": ["thread_001"],
                    }
                ],
                "open_thread_ids": ["thread_001"],
            }
        }
    )

    updated = advance_continuity_ledger(
        legacy_ledger,
        ChapterCandidate(
            chapter_id="chapter_002",
            source_turns=[2],
            markdown="# chapter_002\n\n透は帳簿を確認した。",
        ),
        required_thread_ids=["thread_001"],
        covered_thread_ids=["thread_001"],
        act_id="act_001",
    )

    assert updated.continuity.open_thread_ids == []
    assert updated.continuity.act_summaries[0].chapter_ids == ["chapter_002"]
    assert updated.continuity.character_arcs == []
