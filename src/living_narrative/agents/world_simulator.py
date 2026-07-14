"""World Simulator slot implementation."""

from typing import Any

from living_narrative.agents.event_history import load_recent_events
from living_narrative.agents.models import BackgroundEventCandidate, WorldSimulatorOutput
from living_narrative.agents.pacing import detect_stall
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import WorldEventCandidate
from living_narrative.random.tables import WeightedEntry
from living_narrative.state.models import (
    EncounterEntry,
    Event,
    FactionState,
    ThreatTrack,
    Visibility,
)

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
    faction_events = _faction_events(context)
    pacing_events = _pacing_stall_events(stalled_turns, boost)
    encounter_events = _encounter_events(context)
    return [
        *directive_events,
        *dice_events,
        *background_candidates,
        *threat_events,
        *faction_events,
        *pacing_events,
        *encounter_events,
    ]


def _encounter_events(context: TurnContext) -> list[WorldEventCandidate]:
    history = _encounter_history(context)
    eligible = [
        entry
        for entry in context.bundle.encounters
        if _encounter_is_eligible(context, entry, history)
    ]
    if not eligible:
        return []
    by_id = {entry.id: entry for entry in eligible}
    roll = context.random_engine.select_from_table(
        [WeightedEntry(name=entry.id, weight=entry.weight) for entry in eligible],
        turn=context.turn,
        table_name="encounters",
        label="world_simulator.encounter",
    )
    selected = by_id[str(roll.result)]
    return [
        WorldEventCandidate(
            type="encounter",
            cause="world_simulator",
            text=selected.text,
            visibility=selected.visibility,
            effects={
                "encounter_id": selected.id,
                "roll_id": roll.id,
                "_roll": roll.model_dump(mode="json"),
            },
        )
    ]


def _encounter_history(context: TurnContext) -> list[Event]:
    """Load append-only encounter events, preserving fail-soft history semantics."""
    if context.paths is None:
        return []
    return load_recent_events(
        context.paths.runs,
        context.bundle.timeline,
        max_turns=len(context.bundle.timeline),
    )


def _encounter_is_eligible(
    context: TurnContext, entry: EncounterEntry, history: list[Event] | None = None
) -> bool:
    if entry.scene_id is not None and not any(
        scene.id == entry.scene_id and scene.status == "active" for scene in context.bundle.scenes
    ):
        return False
    if entry.threat is None:
        threat_eligible = True
    else:
        threat = next(
            (item for item in context.bundle.world.threats if item.id == entry.threat.threat_id),
            None,
        )
        if threat is None:
            return False
        if entry.threat.min_pressure is not None and threat.pressure < entry.threat.min_pressure:
            return False
        reached_stages = sum(stage.at <= threat.pressure for stage in threat.stages)
        threat_eligible = entry.threat.min_stage is None or reached_stages >= entry.threat.min_stage

    if not threat_eligible:
        return False
    return _recurrence_is_eligible(
        context, entry, history if history is not None else _encounter_history(context)
    )


def _recurrence_is_eligible(
    context: TurnContext, entry: EncounterEntry, history: list[Event]
) -> bool:
    prior = [
        event
        for event in history
        if event.turn < context.turn
        and event.type == "encounter"
        and event.effects.get("encounter_id") == entry.id
    ]
    if not prior:
        return True

    recurrence = getattr(entry, "recurrence", "cooldown")
    recurrence = getattr(recurrence, "value", recurrence)
    last = max(prior, key=lambda event: event.turn)
    if recurrence == "once":
        return False
    if recurrence == "unlimited":
        return last.turn != context.turn - 1

    cooldown_turns = getattr(entry, "cooldown_turns", None)
    if cooldown_turns is None:
        cooldown_turns = max(1, context.bundle.world.pacing.stall_window)
    return context.turn - last.turn > cooldown_turns


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


def _faction_events(context: TurnContext) -> list[WorldEventCandidate]:
    """Issue 017: at most one faction can make one stateful move per turn."""
    if not context.bundle.factions:
        return []
    faction = context.bundle.factions[0]
    resource_key = _first_key(faction.resources)
    relation_key = _first_key(faction.relations)
    if resource_key is None and relation_key is None:
        return []
    resource_deltas = {resource_key: -5} if resource_key is not None else {}
    relation_deltas = {relation_key: 5} if relation_key is not None else {}
    return [
        WorldEventCandidate(
            type="faction_move",
            cause="world_simulator",
            text=_faction_move_text(faction, resource_key, relation_key),
            visibility=Visibility.GM_ONLY,
            effects={
                "faction_id": faction.id,
                "resource_deltas": resource_deltas,
                "relation_deltas": relation_deltas,
            },
        )
    ]


def _first_key(values: dict[str, int]) -> str | None:
    return next(iter(sorted(values)), None)


def _faction_move_text(
    faction: FactionState, resource_key: str | None, relation_key: str | None
) -> str:
    parts = [f"{faction.name}が次の一手を進める"]
    if resource_key is not None:
        parts.append(f"{resource_key}-5")
    if relation_key is not None:
        parts.append(f"{relation_key}+5")
    return " / ".join(parts)


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
    if _is_character_check(item, constraints):
        return _character_check_event(context, item, constraints)

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
        effects={"roll_id": roll.id, "_roll": roll.model_dump(mode="json")},
    )


def _is_character_check(item: dict[str, Any], constraints: dict[str, Any]) -> bool:
    target = item.get("target") or {}
    return target.get("kind") == "character" or any(
        key in constraints for key in ("character_id", "stat", "skill")
    )


def _character_check_event(
    context: TurnContext,
    item: dict[str, Any],
    constraints: dict[str, Any],
) -> WorldEventCandidate:
    target = item.get("target") or {}
    character_id = constraints.get("character_id") or target.get("id")
    if not isinstance(character_id, str) or not character_id:
        raise ValueError("character check requires character_id or character target id")
    character = next(
        (candidate for candidate in context.bundle.characters if candidate.id == character_id),
        None,
    )
    if character is None:
        raise ValueError(f"character not found: {character_id}")

    check_target = constraints.get("target")
    if isinstance(check_target, bool) or not isinstance(check_target, int):
        raise ValueError("character check target must be an integer from 0 to 100")
    if not 0 <= check_target <= 100:
        raise ValueError("character check target must be from 0 to 100")

    modifiers: dict[str, int] = {}
    for field_name in ("stat", "skill"):
        name = constraints.get(field_name)
        if name is None:
            continue
        if not isinstance(name, str) or not name:
            raise ValueError(f"character check {field_name} must be a non-empty string")
        values = getattr(character, f"{field_name}s")
        if name not in values:
            raise ValueError(f"{field_name} not found for {character_id}: {name}")
        modifiers[f"{field_name}:{name}"] = values[name]
    if not modifiers:
        raise ValueError("character check requires stat or skill")

    roll = context.random_engine.roll_chance(
        check_target,
        modifiers,
        turn=context.turn,
        label=f"intervention:{item['id']}",
    )
    return WorldEventCandidate(
        type="dice_roll_request",
        cause=f"intervention:{item['id']}",
        text=item.get("content", "character check"),
        visibility=item["visibility"],
        effects={
            "character_id": character_id,
            "stat": constraints.get("stat"),
            "skill": constraints.get("skill"),
            "roll_id": roll.id,
            "_roll": roll.model_dump(mode="json"),
        },
        target_id=character_id,
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
