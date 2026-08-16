"""Deterministic chapter-quality review primitives."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from living_narrative.book.chapters import ChapterCandidate, ChapterContext


class ChapterReviewDecision(StrEnum):
    ACCEPT = "accept"
    REVISE = "revise"


class ChapterReviewMetrics(BaseModel):
    body_units: int = Field(ge=0)
    min_units: int = Field(ge=1)
    max_units: int = Field(ge=1)


class ChapterReview(BaseModel):
    chapter_id: str
    decision: ChapterReviewDecision
    metrics: ChapterReviewMetrics
    reasons: list[str] = Field(default_factory=list)


def _body_units(markdown: str) -> int:
    """Count CJK characters and word-like Latin tokens without model-dependent tokenizers."""
    body = markdown.partition("\n\n")[2]
    cjk = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", body)
    latin_tokens = re.findall(r"[A-Za-z0-9]+", body)
    return len(cjk) + len(latin_tokens)


def review_chapter(context: ChapterContext, candidate: ChapterCandidate) -> ChapterReview:
    """Evaluate a candidate with deterministic, inspectable hard gates only."""
    if candidate.chapter_id != context.chapter_id:
        raise ValueError("candidate chapter_id does not match chapter context")
    units = _body_units(candidate.markdown)
    reasons: list[str] = []
    if units < context.target_min_words:
        reasons.append(f"body units {units} below minimum {context.target_min_words}")
    if units > context.target_max_words:
        reasons.append(f"body units {units} above maximum {context.target_max_words}")
    return ChapterReview(
        chapter_id=context.chapter_id,
        decision=ChapterReviewDecision.REVISE if reasons else ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(
            body_units=units,
            min_units=context.target_min_words,
            max_units=context.target_max_words,
        ),
        reasons=reasons,
    )
