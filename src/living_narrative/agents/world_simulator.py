"""World Simulator slot implementation."""

from typing import Any

from living_narrative.agents.models import BackgroundEventCandidate, WorldSimulatorOutput
from living_narrative.agents.pacing import detect_stall
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import WorldEventCandidate
from living_narrative.random.tables import WeightedEntry
from living_narrative.state.models import ThreatTrack, Visibility

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
    table_entries = context.bundle.world.background_events
    if table_entries:
        entries = [WeightedEntry(name=entry.text, weight=entry.weight) for entry in table_entries]
    else:
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
    stalled_turns = detect_stall(context)
    boost = context.bundle.world.pacing.pressure_boost if stalled_turns is not None else 0
    threat_events = [
        event
        for threat in context.bundle.world.threats
        for event in _threat_events(context, threat, boost=boost)
    ]
    pacing_events = _pacing_stall_events(stalled_turns, boost)
    return [
        *directive_events,
        *dice_events,
        *background_candidates,
        *threat_events,
        *pacing_events,
    ]


def _threat_events(
    context: TurnContext, threat: ThreatTrack, *, boost: int = 0
) -> list[WorldEventCandidate]:
    """Issue 008: roll the threat's pressure forward and fire any newly-crossed stages.

    Issue 011: when the story has stalled, ``boost`` is appended to the pressure roll's dice
    notation (e.g. ``2d6`` -> ``2d6+4``) to escalate faster.
    """
    notation = f"{threat.pressure_per_turn}+{boost}" if boost else threat.pressure_per_turn
    roll = context.random_engine.roll_dice(
        notation,
        turn=context.turn,
        label=f"threat:{threat.id}",
    )
    old_pressure = threat.pressure
    new_pressure = min(100, old_pressure + roll.result)
    pressure_event = WorldEventCandidate(
        type="threat_pressure",
        cause="world_simulator",
        text=f"{threat.name}の気配が強まっている(pressure {new_pressure})",
        visibility=Visibility.GM_ONLY,
        effects={
            "threat_id": threat.id,
            "pressure": new_pressure,
            "roll_id": roll.id,
            "_roll": roll.model_dump(mode="json"),
        },
    )
    stage_events = [
        WorldEventCandidate(
            type="threat_stage",
            cause="world_simulator",
            text=stage.text,
            visibility=stage.visibility,
            effects={
                **stage.effects,
                "threat_id": threat.id,
                "stage_at": stage.at,
                "roll_id": roll.id,
            },
        )
        for stage in sorted(threat.stages, key=lambda item: item.at)
        if old_pressure < stage.at <= new_pressure
    ]
    return [pressure_event, *stage_events]


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


def _pacing_stall_events(stalled_turns: int | None, boost: int) -> list[WorldEventCandidate]:
    """Issue 011: a single gm_only note when Simulate escalated threat pressure for a stall."""
    if stalled_turns is None:
        return []
    return [
        WorldEventCandidate(
            type="pacing_stall",
            cause="world_simulator",
            text=f"物語が{stalled_turns}ターン前進していないため、脅威の圧力を強める。",
            visibility=Visibility.GM_ONLY,
            effects={"stalled_turns": stalled_turns, "pressure_boost": boost},
        )
    ]
