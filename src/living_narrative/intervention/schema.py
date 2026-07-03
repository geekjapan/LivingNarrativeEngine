"""Intervention schema (project_plan.md §14.8): the 15 types and their handling status."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from living_narrative.state.ids import id_type, validate_relationship_key
from living_narrative.state.models import UserMode, Visibility

InterventionId = id_type("int")

TargetKind = Literal[
    "world", "character", "scene", "reader_state", "canon", "gm_vault", "relationship", "roll"
]


class InterventionType(StrEnum):
    SCENE_DIRECTIVE = "scene_directive"
    CHARACTER_DIRECTIVE = "character_directive"
    WORLD_DIRECTIVE = "world_directive"
    EVENT_INJECTION = "event_injection"
    PROBABILITY_BIAS = "probability_bias"
    TONE_CONTROL = "tone_control"
    PACING_CONTROL = "pacing_control"
    REVEAL_CONTROL = "reveal_control"
    HIDDEN_TRUTH_EDIT = "hidden_truth_edit"
    CANON_EDIT = "canon_edit"
    DICE_ROLL_REQUEST = "dice_roll_request"
    STOP_CONDITION = "stop_condition"
    SCENE_PIVOT = "scene_pivot"
    RELATIONSHIP_EDIT = "relationship_edit"
    MEMORY_EDIT = "memory_edit"


class HandlingStatus(StrEnum):
    """tasks.md 1.5: which of the 3 buckets a ``type`` falls into."""

    ROUTED = "routed"
    DELEGATED = "delegated"
    UNHANDLED = "unhandled"


HANDLING_STATUS: dict[InterventionType, HandlingStatus] = {
    InterventionType.SCENE_DIRECTIVE: HandlingStatus.ROUTED,
    InterventionType.CHARACTER_DIRECTIVE: HandlingStatus.ROUTED,
    InterventionType.WORLD_DIRECTIVE: HandlingStatus.ROUTED,
    InterventionType.EVENT_INJECTION: HandlingStatus.ROUTED,
    InterventionType.TONE_CONTROL: HandlingStatus.ROUTED,
    InterventionType.REVEAL_CONTROL: HandlingStatus.ROUTED,
    InterventionType.DICE_ROLL_REQUEST: HandlingStatus.ROUTED,
    InterventionType.CANON_EDIT: HandlingStatus.ROUTED,
    InterventionType.HIDDEN_TRUTH_EDIT: HandlingStatus.ROUTED,
    InterventionType.STOP_CONDITION: HandlingStatus.DELEGATED,
    InterventionType.PROBABILITY_BIAS: HandlingStatus.UNHANDLED,
    InterventionType.PACING_CONTROL: HandlingStatus.UNHANDLED,
    InterventionType.SCENE_PIVOT: HandlingStatus.UNHANDLED,
    InterventionType.RELATIONSHIP_EDIT: HandlingStatus.UNHANDLED,
    InterventionType.MEMORY_EDIT: HandlingStatus.UNHANDLED,
}

ROUTED_TYPES = frozenset(t for t, s in HANDLING_STATUS.items() if s == HandlingStatus.ROUTED)
DELEGATED_TYPES = frozenset(t for t, s in HANDLING_STATUS.items() if s == HandlingStatus.DELEGATED)
UNHANDLED_TYPES = frozenset(t for t, s in HANDLING_STATUS.items() if s == HandlingStatus.UNHANDLED)


class InterventionTarget(BaseModel):
    """``target`` (spec.md Requirement "Interventionスキーマ"): nested, never flattened."""

    kind: TargetKind
    id: str | None = None

    @model_validator(mode="after")
    def _validate_relationship_id(self) -> "InterventionTarget":
        if self.kind == "relationship" and self.id is not None:
            validate_relationship_key(self.id)
        return self


class InterventionDraft(BaseModel):
    """The Interpreter/direct-input payload shape: no ``id``/``turn``/``user_role`` (D1)."""

    type: InterventionType
    target: InterventionTarget
    content: str = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)
    visibility: Visibility


class Intervention(BaseModel):
    id: InterventionId
    turn: int
    user_role: UserMode
    type: InterventionType
    target: InterventionTarget
    content: str = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)
    visibility: Visibility
