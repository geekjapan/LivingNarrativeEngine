from __future__ import annotations

from living_narrative.book.chapters import build_chapter_context, compile_chapter
from living_narrative.state.models import (
    BookActPlan,
    BookChapterPlan,
    BookLedgerState,
    BookPlanState,
    BookWordRange,
    CharacterState,
    MemorySummary,
    ReaderStateEntry,
    SceneState,
    Visibility,
    WorldState,
    WorldStateBundle,
)


def _bundle() -> WorldStateBundle:
    return WorldStateBundle(
        world=WorldState(id="world_001", name="霧の駅", summary="station"),
        characters=[
            CharacterState(
                id="char_001",
                name="澪",
                role="探偵",
                secrets=["犯人を知っている"],
                private_mind=["このことは隠す"],
            )
        ],
        scenes=[
            SceneState(
                id="scene_001",
                location="ホーム",
                time="夜",
                reader_visible_facts=["時計が逆向きに進んでいる"],
            )
        ],
        reader_state=[
            ReaderStateEntry(
                id="reader_state_001",
                text="列車はまだ到着していない。",
                established_turn=1,
                disclosed_turn=1,
            )
        ],
        memory_summaries=[MemorySummary(id="memory_001", up_to_turn=3, text="澪は時計を調べた。")],
        book_plan=BookPlanState(
            premise="帰還経路を探す。",
            audience="mystery readers",
            acts=[BookActPlan(id="act_001", promise="異常を知る", chapter_ids=["chapter_001"])],
            chapters=[
                BookChapterPlan(
                    id="chapter_001",
                    act_id="act_001",
                    planned_goal="時刻表の矛盾を発見する。",
                    required_thread_ids=[],
                    target_word_range=BookWordRange(min_words=100, max_words=500),
                )
            ],
        ),
        book_ledger=BookLedgerState(),
    )


def test_chapter_context_contains_only_reader_safe_state_and_plan():
    context = build_chapter_context(_bundle(), "chapter_001", source_turns=[1, 2, 3])

    assert context.chapter_id == "chapter_001"
    assert context.planned_goal == "時刻表の矛盾を発見する。"
    assert context.reader_facts == ["列車はまだ到着していない。", "時計が逆向きに進んでいる"]
    assert context.memory_summary == "澪は時計を調べた。"
    serialized = context.model_dump_json()
    assert "犯人を知っている" not in serialized
    assert "このことは隠す" not in serialized
    assert Visibility.GM_ONLY.value not in serialized


def test_chapter_compiler_emits_deterministic_provenance_markdown():
    context = build_chapter_context(_bundle(), "chapter_001", source_turns=[1, 2])

    candidate = compile_chapter(
        context,
        ["ホームの時計は逆向きに進んでいた。", "澪は時刻表の余白に気づいた。"],
    )

    assert candidate.chapter_id == "chapter_001"
    assert candidate.source_turns == [1, 2]
    assert candidate.markdown.startswith("---\nchapter_id: chapter_001\n")
    assert "時刻表の矛盾を発見する。" in candidate.markdown
    assert "澪は時刻表の余白に気づいた。" in candidate.markdown
