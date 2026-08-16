"""Reader-safe context construction and deterministic chapter compilation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from living_narrative.state.models import WorldStateBundle, latest_memory_summary


class ChapterContext(BaseModel):
    """Inputs that may safely be used to create or review one chapter."""

    chapter_id: str
    act_id: str
    planned_goal: str
    required_thread_ids: list[str] = Field(default_factory=list)
    target_min_words: int
    target_max_words: int
    reader_facts: list[str] = Field(default_factory=list)
    memory_summary: str = ""
    source_turns: list[int] = Field(default_factory=list)


class ChapterCandidate(BaseModel):
    """Deterministic chapter artifact with its complete turn provenance."""

    chapter_id: str
    source_turns: list[int]
    markdown: str


def build_chapter_context(
    bundle: WorldStateBundle,
    chapter_id: str,
    *,
    source_turns: list[int],
) -> ChapterContext:
    """Build a context projection without GM-only or character-private state."""
    chapter = bundle.book_plan.chapter(chapter_id)
    reader_facts = [entry.text for entry in bundle.reader_state]
    for scene in bundle.scenes:
        reader_facts.extend(scene.reader_visible_facts)
    return ChapterContext(
        chapter_id=chapter.id,
        act_id=chapter.act_id,
        planned_goal=chapter.planned_goal,
        required_thread_ids=list(chapter.required_thread_ids),
        target_min_words=chapter.target_word_range.min_words,
        target_max_words=chapter.target_word_range.max_words,
        reader_facts=reader_facts,
        memory_summary=latest_memory_summary(bundle.memory_summaries),
        source_turns=sorted(set(source_turns)),
    )


def compile_chapter(context: ChapterContext, narration_segments: list[str]) -> ChapterCandidate:
    """Compile reviewed reader-visible narration into a provenance-rich Markdown artifact."""
    body = "\n\n".join(segment.strip() for segment in narration_segments if segment.strip())
    markdown = "\n".join(
        [
            "---",
            f"chapter_id: {context.chapter_id}",
            f"act_id: {context.act_id}",
            f"source_turns: {context.source_turns}",
            "---",
            "",
            f"# {context.chapter_id}",
            "",
            f"> Planned goal: {context.planned_goal}",
            "",
            body,
            "",
        ]
    )
    return ChapterCandidate(
        chapter_id=context.chapter_id,
        source_turns=context.source_turns,
        markdown=markdown,
    )
