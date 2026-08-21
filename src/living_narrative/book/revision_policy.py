"""Deterministic author-facing revision policy for reader-safe review findings."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from living_narrative.book.review import (
    ChapterReview,
    SemanticContinuityFinding,
    SemanticFindingCategory,
)


class RevisionAction(StrEnum):
    """The smallest author-visible scope that can repair a finding."""

    PART_REVISE = "part_revise"
    REPLAN = "replan"
    ACT_REDESIGN = "act_redesign"


class RevisionFindingDecision(BaseModel):
    """One immutable, reader-safe recommendation derived from one review finding."""

    finding_code: str
    category: SemanticFindingCategory
    severity: str
    subject_ids: list[str] = Field(default_factory=list)
    action: RevisionAction
    repair_instruction: str


class RevisionPolicyDecision(BaseModel):
    """The deterministic revision scope and its reader-safe supporting decisions."""

    action: RevisionAction
    requires_author_action: bool
    findings: list[RevisionFindingDecision] = Field(default_factory=list)


_ACTION_BY_CATEGORY = {
    SemanticFindingCategory.ACT_PROMISE: RevisionAction.ACT_REDESIGN,
    SemanticFindingCategory.REQUIRED_THREAD: RevisionAction.REPLAN,
    SemanticFindingCategory.CHARACTER_ARC: RevisionAction.REPLAN,
    SemanticFindingCategory.POINT_OF_VIEW: RevisionAction.PART_REVISE,
    SemanticFindingCategory.CHARACTER_RELATION: RevisionAction.PART_REVISE,
    SemanticFindingCategory.FORESHADOWING: RevisionAction.PART_REVISE,
    SemanticFindingCategory.OTHER: RevisionAction.PART_REVISE,
}
_ACTION_PRIORITY = {
    RevisionAction.PART_REVISE: 1,
    RevisionAction.REPLAN: 2,
    RevisionAction.ACT_REDESIGN: 3,
}


def _decision_for_finding(finding: SemanticContinuityFinding) -> RevisionFindingDecision:
    return RevisionFindingDecision(
        finding_code=finding.code,
        category=finding.category,
        severity=finding.severity,
        subject_ids=list(finding.subject_ids),
        action=_ACTION_BY_CATEGORY[finding.category],
        repair_instruction=finding.repair_instruction,
    )


def decide_revision_policy(review: ChapterReview) -> RevisionPolicyDecision:
    """Map reader-safe semantic findings to one explicit, author-approved revision scope.

    This function never changes a lifecycle state and never accepts a chapter. Its result is
    advisory evidence for the author and becomes durable provenance when a revised attempt is
    recorded.
    """
    semantic_findings = review.semantic.findings if review.semantic is not None else []
    findings = [_decision_for_finding(finding) for finding in semantic_findings]
    action = max(
        (finding.action for finding in findings),
        key=lambda item: _ACTION_PRIORITY[item],
        default=RevisionAction.PART_REVISE,
    )
    return RevisionPolicyDecision(
        action=action,
        requires_author_action=any(finding.severity == "block" for finding in findings),
        findings=findings,
    )
