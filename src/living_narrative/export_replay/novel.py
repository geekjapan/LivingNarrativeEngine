"""LLM prose pass over a chapter outline (docs/issues/027): one LLM call per chapter that
smooths repetition/seams left by stitching per-turn narration together, never inventing new
facts. This is an export-time editorial pass, separate from (and using a different prompt than)
the in-pipeline ``narration/llm_narrator.py`` narrator.

Failure of a single chapter's LLM call falls back to that chapter's raw narration
concatenation and continues with the rest of the chapters — never fails the whole export
(mirrors ADR-0002's narrator fallback policy).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from living_narrative.export_replay.outline import Chapter, Outline
from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.state.models import ProjectConfig

logger = logging.getLogger(__name__)

DEFAULT_PROFILE = "prose"
PROMPT_TEMPLATE_NAME = "export-novel-editor-v1"

SYSTEM_PROMPT = """\
あなたは小説の推敲者です。渡された章の地文素材を、読める一続きの小説の一章に整えてください。\
これはパイプライン外の書き出し(エクスポート)専用の作業で、物語本体の生成ではありません。

## 禁止事項(厳守)
- 素材(narration_material / key_events)にない新しい事実・出来事・人物の内心・固有名詞を発明しない。
- 隠された真相や、素材に書かれていない裏設定を推測で書き足さない。

## 作業内容
- 素材内の反復表現(場面説明の繰り返しなど)を削る。
- ターンをまたぐ際の継ぎ目を自然に平滑化する。
- 視点・時制を三人称・現在時制に統一する。
- previous_synopsis(前章までのあらすじ)を踏まえ、この章がその続きとして自然に読めるようにする\
(previous_synopsis が空文字ならこの章がセッションの冒頭)。

## 出力
- chapter_text: この章の完成した地文(素材にある内容のみで構成する)。
- synopsis: 次の章に引き継ぐための、この章までの物語の200字程度の日本語要約。
"""


class NovelChapterOutput(BaseModel):
    chapter_text: str = Field(min_length=1)
    synopsis: str = Field(min_length=1)


def _chapter_payload(
    project: ProjectConfig, chapter: Chapter, previous_synopsis: str
) -> dict[str, Any]:
    return {
        "genre": project.genre,
        "tone": project.tone,
        "previous_synopsis": previous_synopsis,
        "narration_material": "\n\n".join(chapter.narration_texts),
        "key_events": [
            {"turn": event.turn, "type": event.type, "text": event.text}
            for event in chapter.key_events
        ],
    }


def _raw_fallback_text(chapter: Chapter) -> str:
    body = "\n\n".join(chapter.narration_texts).rstrip("\n")
    marker = "<!-- fallback: raw narration -->"
    return f"{body}\n\n{marker}" if body else marker


def render_novel(
    project: ProjectConfig,
    outline: Outline,
    gateway: LLMGateway,
    profile: str = DEFAULT_PROFILE,
) -> str:
    """Render ``outline`` into a novel-draft Markdown string, one LLM call per chapter.

    ``profile`` is the binding key passed straight through to ``gateway.complete`` (the same
    mechanism ``narration/llm_narrator.py`` uses) — it defaults to ``"prose"``, which is not
    part of spec-foundation D122's frozen binding-key enum, so it only resolves to a distinct
    provider if the caller also configures ``llm_bindings`` at the schema level in a future
    change; absent that it always falls back to the project's default ``llm`` profile, same as
    any other unbound key.
    """
    lines = [
        f"# {project.title} — 小説風ドラフト(自動生成)",
        "",
        "> このプレイセッションのログから自動生成した初稿です。人手の推敲を前提とします。",
        "",
    ]
    previous_synopsis = ""
    for chapter in outline.chapters:
        payload = _chapter_payload(project, chapter, previous_synopsis)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        try:
            output = gateway.complete(
                profile, messages, NovelChapterOutput, prompt_template_name=PROMPT_TEMPLATE_NAME
            )
            assert isinstance(output, NovelChapterOutput)
            chapter_text = output.chapter_text.strip()
            previous_synopsis = output.synopsis.strip()
        except (ProviderConnectionError, StructuredOutputError) as exc:
            logger.warning(
                "chapter %d prose pass failed (%s), falling back to raw narration",
                chapter.index,
                exc,
            )
            chapter_text = _raw_fallback_text(chapter)
            # previous_synopsis is left unchanged so the next chapter still gets continuity.

        lines.append(f"## 第{chapter.index}章: {chapter.title}")
        lines.append("")
        lines.append(chapter_text)
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"
