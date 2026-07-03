"""Pydantic models for turn-pipeline artifacts and slot inputs/outputs (design.md D3)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import CharacterId, Event, Visibility

CheckSeverity = Literal["info", "warn", "error"]


class InterventionFile(BaseModel):
    """``intervention.yaml``: the turn's confirmed interventions, plus any permission rejections."""

    turn: int
    interventions: list[dict[str, Any]] = Field(default_factory=list)
    rejections: list[dict[str, Any]] = Field(default_factory=list)


class WorldEventCandidate(BaseModel):
    """A candidate world event proposed by the Simulate slot, before an id is assigned."""

    type: str
    cause: str | None = None
    text: str
    visibility: Visibility
    known_by: list[CharacterId] = Field(default_factory=list)
    hidden_from: list[CharacterId] = Field(default_factory=list)
    effects: dict[str, Any] = Field(default_factory=dict)
    target_id: str | None = None


class ActionCandidate(BaseModel):
    """A single character's proposed action, produced by the Act slot."""

    character_id: CharacterId
    action_text: str = Field(min_length=1)
    kind: Literal["action", "dialogue", "inner_reaction"] = "action"
    visibility: Visibility = Visibility.READER
    target_id: str | None = None
    effects: dict[str, Any] = Field(default_factory=dict)
    source_index: int | None = None


class ActRecord(BaseModel):
    """One Act-phase LLM call, persisted under ``agent_io/``."""

    character_id: CharacterId
    prompt_template_name: str
    request: list[dict[str, Any]]
    response: dict[str, Any]
    input_context: dict[str, Any] = Field(default_factory=dict)


class RejectedChange(BaseModel):
    """A state-diff change candidate the BuildDiff slot declined to propose, with why."""

    change: StateDiffChange
    reason: str


class BuildDiffOutput(BaseModel):
    diff: StateDiff
    rejected_changes: list[RejectedChange] = Field(default_factory=list)
    synthetic_events: list[Event] = Field(default_factory=list)


class CheckResult(BaseModel):
    severity: CheckSeverity
    message: str
    source: str | None = None
    related_ids: list[str] = Field(default_factory=list)


class ErrorReport(BaseModel):
    """Human-readable failure record embedded in ``meta.yaml`` when a turn is ``failed``."""

    phase: str
    exception_type: str
    message: str
