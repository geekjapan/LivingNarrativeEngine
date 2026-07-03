"""Turn status model (spec-foundation.md D111, §3)."""

from enum import StrEnum


class TurnStatus(StrEnum):
    APPLIED = "applied"
    PENDING_REVIEW = "pending_review"
    STOPPED_FOR_REVIEW = "stopped_for_review"
    FAILED = "failed"


UNRESOLVED_STATUSES = {TurnStatus.PENDING_REVIEW, TurnStatus.STOPPED_FOR_REVIEW}
