"""Protocols for the 5 registry-swappable slots (design.md D2/D113)."""

from collections.abc import Callable
from typing import Any, Protocol

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.pipeline.models import (
    ActionCandidate,
    ActRecord,
    BuildDiffOutput,
    CheckResult,
    WorldEventCandidate,
)
from living_narrative.random.models import Roll
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event


class SimulateSlot(Protocol):
    def __call__(
        self, context: TurnContext, interventions: list[dict[str, Any]]
    ) -> list[WorldEventCandidate]: ...


class ActSlot(Protocol):
    def __call__(
        self,
        context: TurnContext,
        world_events: list[WorldEventCandidate],
        gateway: LLMGateway,
        interventions: list[dict[str, Any]] = (),
    ) -> tuple[list[ActionCandidate], list[ActRecord]]: ...


class ResolveSlot(Protocol):
    def __call__(
        self,
        context: TurnContext,
        world_events: list[WorldEventCandidate],
        action_candidates: list[ActionCandidate],
        allocate_event_id: Callable[[], str],
        record_roll: Callable[[Roll], None],
    ) -> list[Event]: ...


class BuildDiffSlot(Protocol):
    def __call__(
        self,
        context: TurnContext,
        resolved_events: list[Event],
        interventions: list[dict[str, Any]],
        allocate_event_id: Callable[[], str] | None = None,
    ) -> BuildDiffOutput: ...


class CheckSlot(Protocol):
    def __call__(
        self,
        context: TurnContext,
        narration_text: str,
        resolved_events: list[Event],
        diff_candidate: StateDiff,
    ) -> list[CheckResult]: ...
