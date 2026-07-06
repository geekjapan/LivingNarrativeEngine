"""Whole-draft revision pass over an existing ``novel_draft.md`` (docs/issues/030 — Track C's
final DAG node). Two LLM stages:

1. **Whole-draft analysis (one call)**: every chapter's text is sent to the LLM in one shot to
   surface repeated phrases, style drift, and cross-chapter continuity notes as structured
   ``RevisionNotes``. This stage sees the whole draft because repetition/inconsistency is only
   visible across chapters, not within one — 027's per-chapter ``render_novel`` pass cannot catch
   it by construction.
2. **Per-chapter smoothing (one call per chapter)**: each chapter's text, the ``RevisionNotes``
   from stage 1, and a short window of the previous/next chapter's text (their last/first ~200
   characters, taken from the *original*, pre-revision draft — each chapter call is independent
   of every other chapter's revision outcome, unlike ``render_novel``'s sequential synopsis
   chaining) are sent to the LLM with a narrow mandate: reduce the flagged repeated phrases,
   unify style, and smooth chapter-to-chapter seams. Plot/dialogue meaning must not change and no
   new facts may be invented (mirrors 027's ``render_novel`` constraint).

Failure policy (deliberately asymmetric from 027):

- Stage 1 (whole-draft analysis) failing means we have no revision notes to act on at all, so
  silently treating the original draft as "revised" would misrepresent what happened. It raises
  ``RevisionNotesError`` instead — the caller (the CLI) should surface this as a hard error.
- Stage 2 (per-chapter smoothing) failing is scoped to one chapter, so it falls back to that
  chapter's original text plus an HTML comment marker and continues with the rest — same
  fallback philosophy as ``novel.py``'s per-chapter raw-narration fallback.

Markdown contract with ``novel.py``'s ``render_novel`` output: chapters are demarcated by
``"## 第N章: <title>"`` headings (one per chapter, in order), preceded by an arbitrary preamble
block (title/blurb). ``parse_novel_draft`` parses that contract back into a
``(preamble, [(title, text), ...])`` pair; ``render_revised_novel`` renders the same contract
back out. We parse the rendered Markdown headings rather than threading the ``Outline``/``Chapter``
objects through, because ``export revise`` is designed to run standalone against *any* existing
``novel_draft.md`` (see docs/issues/030's CLI design item 2) — including ones from a prior process
or a hand-edited draft — not only ones produced in the same invocation as ``export novel``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.pipeline.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

DEFAULT_REVISION_PROFILE = "prose"
NOTES_PROMPT_TEMPLATE_NAME = "export-revision-notes-v1"
CHAPTER_PROMPT_TEMPLATE_NAME = "export-revision-chapter-v1"

_CONTEXT_CHARS = 200
_CHAPTER_HEADING_RE = re.compile(r"^## 第\d+章: (.*)$", re.MULTILINE)
_FAILED_CHAPTER_MARKER = "<!-- revision failed: original kept -->"

_NOTES_SYSTEM_PROMPT = """\
あなたは小説の推敲者です。渡された小説の全章を通して読み、以下を構造化して指摘してください。\
これは書き出し(エクスポート)専用の分析作業で、本文の書き換えはこの段では行いません。

## 指摘してほしいこと
- repeated_phrases: 複数の章にまたがって繰り返し使われている定型的な描写・言い回し(例:同じ比喩、\
同じ情景描写)。
- style_issues: 章をまたいだ文体のゆらぎ(視点・時制・語尾などの不統一)。
- continuity_notes: 章と章の間で気になる矛盾や、接続が不自然な箇所。

## 禁止事項
- ここでは本文を書き換えない。指摘のみを行う。
- 素材にない出来事や設定を推測で指摘に加えない。
"""

_CHAPTER_SYSTEM_PROMPT = """\
あなたは小説の推敲者です。1章分の本文を、指摘された問題点に沿って整えてください。\
これは書き出し(エクスポート)専用の推敲作業です。

## 作業内容(この範囲に限定する)
- revision_notes で指摘された反復語句を、この章に出てくる分だけ削減する。
- revision_notes で指摘された文体のゆらぎを、この章内で統一する。
- previous_chapter_tail(前章の末尾)・next_chapter_head(次章の冒頭)を踏まえ、\
章の始まりと終わりの接続を自然に平滑化する。

## 禁止事項(厳守)
- 筋・出来事・台詞の意味を変えない。
- この章の本文にない新しい事実・出来事・人物の内心・固有名詞を発明しない。
- previous_chapter_tail / next_chapter_head の内容をこの章の本文に書き足さない \
(接続を滑らかにする参考情報としてのみ使う)。

## 出力
- chapter_text: 整えたあとのこの章の本文。
"""


class RevisionNotes(BaseModel):
    repeated_phrases: list[str] = Field(default_factory=list)
    style_issues: list[str] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)


class ChapterRevisionOutput(BaseModel):
    chapter_text: str = Field(min_length=1)


class RevisionNotesError(RuntimeError):
    """Stage 1 (whole-draft analysis) failed. Raised instead of silently treating the
    original draft as "revised" output."""


class NovelDraftParseError(ValueError):
    """``novel_draft.md``'s contents don't match the ``"## 第N章: ..."`` heading contract."""


def parse_novel_draft(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse a ``render_novel``-shaped Markdown draft into ``(preamble, chapters)``, where
    ``chapters`` is a list of ``(title, text)`` pairs in document order."""
    matches = list(_CHAPTER_HEADING_RE.finditer(markdown))
    if not matches:
        raise NovelDraftParseError(
            "no '## 第N章: ...' chapter headings found — is this a novel_draft.md-shaped file?"
        )

    preamble = markdown[: matches[0].start()].rstrip("\n")
    chapters: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        text = markdown[start:end].strip("\n")
        chapters.append((title, text))
    return preamble, chapters


def render_revised_novel(preamble: str, chapters: list[tuple[str, str]]) -> str:
    """Render ``(preamble, chapters)`` back into the same Markdown contract ``parse_novel_draft``
    reads, renumbering chapter headings sequentially from 1."""
    lines: list[str] = []
    if preamble:
        lines.append(preamble)
        lines.append("")
    for index, (title, text) in enumerate(chapters, start=1):
        lines.append(f"## 第{index}章: {title}")
        lines.append("")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def revise_novel(
    chapters: list[tuple[str, str]],
    gateway: LLMGateway,
    profile: str = DEFAULT_REVISION_PROFILE,
) -> tuple[list[tuple[str, str]], RevisionNotes]:
    """Run the two-stage revision pass over ``chapters`` (``(title, text)`` pairs).

    Returns ``(revised_chapters, notes)``. Raises ``RevisionNotesError`` if stage 1 fails; a
    stage-2 failure on an individual chapter falls back to that chapter's original text (see
    module docstring) and never raises.
    """
    notes = _analyze_notes(chapters, gateway, profile)

    revised: list[tuple[str, str]] = []
    for index, (title, text) in enumerate(chapters):
        previous_tail = chapters[index - 1][1][-_CONTEXT_CHARS:] if index > 0 else ""
        next_head = chapters[index + 1][1][:_CONTEXT_CHARS] if index + 1 < len(chapters) else ""
        revised_text = _revise_chapter(
            title, text, notes, previous_tail, next_head, gateway, profile
        )
        revised.append((title, revised_text))
    return revised, notes


def _analyze_notes(
    chapters: list[tuple[str, str]], gateway: LLMGateway, profile: str
) -> RevisionNotes:
    payload: dict[str, Any] = {
        "chapters": [
            {"index": index + 1, "title": title, "text": text}
            for index, (title, text) in enumerate(chapters)
        ]
    }
    messages = [
        {"role": "system", "content": _NOTES_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    try:
        output = gateway.complete(
            profile, messages, RevisionNotes, prompt_template_name=NOTES_PROMPT_TEMPLATE_NAME
        )
    except (ProviderConnectionError, StructuredOutputError) as exc:
        raise RevisionNotesError(
            f"whole-draft revision analysis failed, aborting revision pass: {exc}"
        ) from exc
    assert isinstance(output, RevisionNotes)
    return output


def _revise_chapter(
    title: str,
    text: str,
    notes: RevisionNotes,
    previous_tail: str,
    next_head: str,
    gateway: LLMGateway,
    profile: str,
) -> str:
    payload: dict[str, Any] = {
        "chapter_title": title,
        "chapter_text": text,
        "revision_notes": notes.model_dump(),
        "previous_chapter_tail": previous_tail,
        "next_chapter_head": next_head,
    }
    messages = [
        {"role": "system", "content": _CHAPTER_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    try:
        output = gateway.complete(
            profile,
            messages,
            ChapterRevisionOutput,
            prompt_template_name=CHAPTER_PROMPT_TEMPLATE_NAME,
        )
        assert isinstance(output, ChapterRevisionOutput)
        return output.chapter_text.strip()
    except (ProviderConnectionError, StructuredOutputError) as exc:
        logger.warning(
            "chapter %r revision pass failed (%s), keeping original chapter text", title, exc
        )
        body = text.rstrip("\n")
        return f"{body}\n\n{_FAILED_CHAPTER_MARKER}" if body else _FAILED_CHAPTER_MARKER
