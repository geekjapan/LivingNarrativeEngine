"""Pydantic schemas for agent-runtime I/O."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from living_narrative.pipeline.models import RejectedChange
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import (
    CharacterId,
    CharacterState,
    Event,
    RelationshipState,
    Visibility,
)


class CharacterAgentInput(BaseModel):
    character_id: CharacterId
    scoped_state: CharacterState
    visible_events: list[Event] = Field(default_factory=list)
    visible_facts: list[str] = Field(default_factory=list)
    relationships: list[RelationshipState] = Field(default_factory=list)
    directives: list[dict[str, Any]] = Field(default_factory=list)


class ActionCandidate(BaseModel):
    kind: Literal["action", "dialogue", "inner_reaction"]
    content: str = Field(min_length=1)
    visibility: Visibility | None = None
    target_id: str | None = None
    effects: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _scope_visibility(self) -> "ActionCandidate":
        # Inner thoughts never reach the reader directly; disclosure happens
        # through explicit reader_state diffs, not through candidate tags.
        if self.kind == "inner_reaction":
            if self.visibility != Visibility.GM_ONLY:
                self.visibility = Visibility.CHARACTER
        elif self.visibility is None:
            self.visibility = Visibility.READER
        return self


class EmotionDeltaCandidate(BaseModel):
    emotion: str
    delta: int
    visibility: Visibility = Visibility.CHARACTER


class GoalUpdateCandidate(BaseModel):
    goal_kind: Literal["short_term", "long_term"]
    content: str = Field(min_length=1)
    visibility: Visibility = Visibility.CHARACTER


class CharacterAgentOutput(BaseModel):
    action_candidates: list[ActionCandidate]
    emotion_deltas: list[EmotionDeltaCandidate]
    goal_updates: list[GoalUpdateCandidate]


class ParameterDriftCandidate(BaseModel):
    parameter: str
    delta: int
    visibility: Visibility


class FactionMoveCandidate(BaseModel):
    faction_id: str
    description: str = Field(min_length=1)
    visibility: Visibility


class BackgroundEventCandidate(BaseModel):
    description: str = Field(min_length=1)
    roll_id: str | None = None
    visibility: Visibility
    target_id: str | None = None
    effects: dict[str, Any] = Field(default_factory=dict)


class WorldSimulatorOutput(BaseModel):
    time_advance: str = ""
    parameter_drifts: list[ParameterDriftCandidate] = Field(default_factory=list)
    faction_moves: list[FactionMoveCandidate] = Field(default_factory=list)
    background_events: list[BackgroundEventCandidate] = Field(default_factory=list)


class ConflictResolverOutput(BaseModel):
    resolved_events: list[Event] = Field(default_factory=list)


class StateManagerOutput(BaseModel):
    state_diff: StateDiff
    rejected_changes: list[RejectedChange] = Field(default_factory=list)
