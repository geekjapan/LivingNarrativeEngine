"""Built-in minimal slot implementations (proposal.md): enough to run a turn end-to-end
with only the mock provider. ``add-agent-runtime`` replaces these via the registry.
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.pipeline.models import (
    ActionCandidate,
    ActRecord,
    BuildDiffOutput,
    CheckResult,
    WorldEventCandidate,
)
from living_narrative.pipeline.registry import SlotRegistry
from living_narrative.random.models import Roll
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import CharacterStatus, Event, Visibility


class _ActionTextResponse(BaseModel):
    action_text: str = Field(min_length=1)


def builtin_simulate(
    context: TurnContext, interventions: list[dict[str, Any]]
) -> list[WorldEventCandidate]:
    """No-op world simulator: proposes no candidate events."""
    return []


def builtin_act(
    context: TurnContext,
    world_events: list[WorldEventCandidate],
    gateway: LLMGateway,
) -> tuple[list[ActionCandidate], list[ActRecord]]:
    """Generates one action candidate for a single alive character via llm-provider."""
    alive = [c for c in context.bundle.characters if c.status == CharacterStatus.ALIVE]
    if not alive:
        return [], []

    character = alive[0]
    messages = [
        {
            "role": "user",
            "content": (
                f"{character.name} として、今のシーンで取る行動を短い日本語の一文で述べてください。"
            ),
        }
    ]
    response = gateway.complete(
        f"character:{character.id}",
        messages,
        _ActionTextResponse,
        prompt_template_name="builtin-act-trivial",
    )
    candidate = ActionCandidate(character_id=character.id, action_text=response.action_text)
    record = ActRecord(
        character_id=character.id,
        prompt_template_name="builtin-act-trivial",
        request=messages,
        response=response.model_dump(mode="json"),
    )
    return [candidate], [record]


def builtin_resolve(
    context: TurnContext,
    world_events: list[WorldEventCandidate],
    action_candidates: list[ActionCandidate],
    allocate_event_id: Callable[[], str],
    record_roll: Callable[[Roll], None],
) -> list[Event]:
    """Pass-through: candidates become events verbatim, with no dice/chance judgement."""
    resolved: list[Event] = [
        Event(
            id=allocate_event_id(),
            turn=context.turn,
            type=candidate.type,
            cause=candidate.cause,
            text=candidate.text,
            visibility=candidate.visibility,
            known_by=candidate.known_by,
            hidden_from=candidate.hidden_from,
            effects=candidate.effects,
        )
        for candidate in world_events
    ]
    resolved.extend(
        Event(
            id=allocate_event_id(),
            turn=context.turn,
            type="character_action",
            text=candidate.action_text,
            visibility=Visibility.READER,
        )
        for candidate in action_candidates
    )
    return resolved


def builtin_build_diff(
    context: TurnContext,
    resolved_events: list[Event],
    interventions: list[dict[str, Any]],
) -> BuildDiffOutput:
    """Minimal implementation: proposes no state changes (agent-runtime's State Manager
    replaces this with the real diff-generation logic; nothing here can leak a
    reveal_control-protected fact since no changes are proposed at all).
    """
    diff = StateDiff(id=f"diff_{context.turn:04d}", turn=context.turn, changes=[])
    return BuildDiffOutput(diff=diff, rejected_changes=[])


def builtin_check(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[CheckResult]:
    """No-op checker: never reports an error/warn/info finding."""
    return []


def register_builtin_slots(registry: SlotRegistry) -> None:
    registry.register("simulate", builtin_simulate)
    registry.register("act", builtin_act)
    registry.register("resolve", builtin_resolve)
    registry.register("build_diff", builtin_build_diff)
    registry.register("check", builtin_check)
