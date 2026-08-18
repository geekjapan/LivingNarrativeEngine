"""Deterministic and semantic chapter-quality review primitives."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from living_narrative.book.chapters import ChapterCandidate, ChapterContext
from living_narrative.book.continuity import strip_chapter_scaffolding


class ChapterReviewDecision(StrEnum):
    ACCEPT = "accept"
    REVISE = "revise"


class ChapterReviewMetrics(BaseModel):
    body_units: int = Field(ge=0)
    min_units: int = Field(ge=1)
    max_units: int = Field(ge=1)


class SemanticContinuityFinding(BaseModel):
    """A model-assessed concern with reviewable evidence and an actionable repair."""

    code: str
    severity: Literal["warn", "block"]
    evidence: str
    repair_instruction: str


class SemanticContinuityAssessment(BaseModel):
    """Reader-safe semantic continuity evaluation for one candidate chapter."""

    required_threads_covered: list[str] = Field(default_factory=list)
    findings: list[SemanticContinuityFinding] = Field(default_factory=list)


class _ContinuityGateway(Protocol):
    def complete(
        self,
        binding_key: str,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel],
        prompt_template_name: str,
    ) -> BaseModel: ...


class ChapterReview(BaseModel):
    chapter_id: str
    decision: ChapterReviewDecision
    metrics: ChapterReviewMetrics
    reasons: list[str] = Field(default_factory=list)
    semantic: SemanticContinuityAssessment | None = None


def _body_units(markdown: str) -> int:
    """Count CJK characters and word-like Latin tokens without model-dependent tokenizers."""
    body = strip_chapter_scaffolding(markdown)
    cjk = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", body)
    latin_tokens = re.findall(r"[A-Za-z0-9]+", body)
    return len(cjk) + len(latin_tokens)


def evaluate_semantic_continuity(
    context: ChapterContext,
    candidate: ChapterCandidate,
    *,
    gateway: _ContinuityGateway,
) -> SemanticContinuityAssessment:
    """Evaluate reader-safe continuity and append deterministic missing-thread blocks.

    The model can identify narrative concerns but cannot waive plan obligations. The returned
    evidence is preserved in the review artifact so an author can understand and challenge a
    revision request.
    """
    if candidate.chapter_id != context.chapter_id:
        raise ValueError("candidate chapter_id does not match chapter context")
    messages = [
        {
            "role": "system",
            "content": (
                "Evaluate narrative continuity using only the provided reader-safe context. "
                "Do not invent hidden facts. Record concise evidence and a concrete repair."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Chapter goal: {context.planned_goal}\n"
                f"Required threads: {context.required_thread_ids}\n"
                f"Reader facts: {context.reader_facts}\n"
                f"Continuity summary: {context.memory_summary}\n"
                f"Book continuity digest: {context.continuity_digest}\n"
                f"Candidate:\n{candidate.markdown}"
            ),
        },
    ]
    raw = gateway.complete(
        "chapter_continuity",
        messages,
        SemanticContinuityAssessment,
        prompt_template_name="book.chapter_continuity.v1",
    )
    assessment = SemanticContinuityAssessment.model_validate(raw)
    covered = set(assessment.required_threads_covered)
    missing = [thread_id for thread_id in context.required_thread_ids if thread_id not in covered]
    findings = list(assessment.findings)
    for thread_id in missing:
        findings.append(
            SemanticContinuityFinding(
                code="required_thread_missing",
                severity="block",
                evidence=f"required thread {thread_id} is not covered",
                repair_instruction=f"Address or deliberately advance {thread_id} in the chapter.",
            )
        )
    return assessment.model_copy(update={"findings": findings})


def review_chapter(
    context: ChapterContext,
    candidate: ChapterCandidate,
    *,
    semantic: SemanticContinuityAssessment | None = None,
) -> ChapterReview:
    """Evaluate deterministic hard gates and optional semantic continuity evidence."""
    if candidate.chapter_id != context.chapter_id:
        raise ValueError("candidate chapter_id does not match chapter context")
    units = _body_units(candidate.markdown)
    reasons: list[str] = []
    if units < context.target_min_words:
        reasons.append(f"body units {units} below minimum {context.target_min_words}")
    if units > context.target_max_words:
        reasons.append(f"body units {units} above maximum {context.target_max_words}")
    if semantic is not None:
        reasons.extend(
            finding.evidence for finding in semantic.findings if finding.severity == "block"
        )
    return ChapterReview(
        chapter_id=context.chapter_id,
        decision=ChapterReviewDecision.REVISE if reasons else ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(
            body_units=units,
            min_units=context.target_min_words,
            max_units=context.target_max_words,
        ),
        reasons=reasons,
        semantic=semantic,
    )
