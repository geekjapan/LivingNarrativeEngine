"""World Simulator slot implementation."""

from typing import Any

from living_narrative.agents.models import BackgroundEventCandidate, WorldSimulatorOutput
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import WorldEventCandidate
from living_narrative.random.tables import WeightedEntry
from living_narrative.state.models import Visibility

# world_directive/event_injection become world event candidates verbatim (spec.md Requirement
# "Type別ルーティング"): they *are* what the World Simulator should propose this turn.
_WORLD_DIRECT_TYPES = frozenset({"world_directive", "event_injection"})


def simulate_world(
    context: TurnContext,
    interventions: list[dict[str, Any]],
) -> list[WorldEventCandidate]:
    directive_events = [
        _world_event_from_intervention(item)
        for item in interventions
        if item.get("type") in _WORLD_DIRECT_TYPES
    ]
    dice_events = [
        _dice_roll_event(context, item)
        for item in interventions
        if item.get("type") == "dice_roll_request"
    ]
    entries = [
        WeightedEntry(name="静かな時間が流れる", weight=3),
        WeightedEntry(name="遠くで不穏な物音がする", weight=1),
    ]
    roll = context.random_engine.select_from_table(
        entries,
        turn=context.turn,
        table_name="background_events",
        label="world_simulator.background_event",
    )
    output = WorldSimulatorOutput(
        time_advance="one_turn",
        background_events=[
            BackgroundEventCandidate(
                description=str(roll.result),
                roll_id=roll.id,
                visibility=Visibility.READER,
                effects={"_roll": roll.model_dump(mode="json")},
            )
        ],
    )
    background_candidates = [
        WorldEventCandidate(
            type="background_event",
            cause="world_simulator",
            text=event.description,
            visibility=event.visibility,
            effects=event.effects,
            target_id=event.target_id,
        )
        for event in output.background_events
    ]
    return [*directive_events, *dice_events, *background_candidates]


def _world_event_from_intervention(item: dict[str, Any]) -> WorldEventCandidate:
    target = item.get("target") or {}
    return WorldEventCandidate(
        type=item["type"],
        cause=f"intervention:{item['id']}",
        text=item["content"],
        visibility=item["visibility"],
        effects=dict(item.get("constraints") or {}),
        target_id=target.get("id"),
    )


def _dice_roll_event(context: TurnContext, item: dict[str, Any]) -> WorldEventCandidate:
    constraints = item.get("constraints") or {}
    notation = constraints.get("notation", "1d100")
    roll = context.random_engine.roll_dice(
        notation,
        turn=context.turn,
        target=constraints.get("target"),
        label=f"intervention:{item['id']}",
    )
    return WorldEventCandidate(
        type="dice_roll_request",
        cause=f"intervention:{item['id']}",
        text=item.get("content", notation),
        visibility=item["visibility"],
        effects={"_roll": roll.model_dump(mode="json")},
    )
