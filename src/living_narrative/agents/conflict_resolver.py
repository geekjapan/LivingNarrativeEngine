"""Conflict Resolver slot implementation."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import ActionCandidate, WorldEventCandidate
from living_narrative.random.models import Roll
from living_narrative.state.models import Event, Visibility

Candidate = ActionCandidate | WorldEventCandidate


class CombatPayload(BaseModel):
    """Validated combat request carried by ``effects.combat``."""

    model_config = {"extra": "forbid", "str_strip_whitespace": True, "strict": True}

    attacker: str = Field(min_length=1)
    defender: str = Field(min_length=1)
    stakes: str = Field(min_length=1)
    stat: str | None = Field(default=None, min_length=1)
    skill: str | None = Field(default=None, min_length=1)
    target: int = Field(ge=0, le=100, strict=True)
    damage: int = Field(gt=0, strict=True)
    life_or_death: bool = False

    @model_validator(mode="after")
    def _validate_engagement(self) -> "CombatPayload":
        if self.attacker == self.defender:
            raise ValueError("combat attacker and defender must differ")
        if self.stat is None and self.skill is None:
            raise ValueError("combat requires stat or skill")
        return self


def resolve_conflicts(
    context: TurnContext,
    world_events: list[WorldEventCandidate],
    action_candidates: list[ActionCandidate],
    allocate_event_id: Callable[[], str],
    record_roll: Callable[[Roll], None],
) -> list[Event]:
    for world_event in world_events:
        raw_roll = world_event.effects.pop("_roll", None)
        if raw_roll is not None:
            record_roll(Roll.model_validate(raw_roll))

    ordered = _order_candidates(context, action_candidates, world_events)
    prepared_combat: dict[int, tuple[CombatPayload, dict[str, int]]] = {}
    rejected_combat: dict[int, str] = {}
    for index, candidate in enumerate(ordered):
        if "combat" not in candidate.effects:
            continue
        try:
            prepared_combat[index] = _prepare_combat(context, candidate)
        except (ValidationError, ValueError) as exc:
            rejected_combat[index] = _combat_rejection_reason(exc)

    resolved: list[Event] = []
    handled: set[int] = set()
    for index, candidate in enumerate(ordered):
        if index in handled:
            continue
        if index in rejected_combat:
            resolved.append(
                _combat_rejected_event(
                    context, candidate, allocate_event_id(), rejected_combat[index]
                )
            )
            handled.add(index)
            continue
        conflict_indexes = [
            other_index
            for other_index, other in enumerate(ordered)
            if other_index >= index
            and other_index not in rejected_combat
            and _conflicts(candidate, other)
        ]
        if len(conflict_indexes) <= 1:
            resolved.append(
                _resolve_winner(
                    context,
                    candidate,
                    allocate_event_id(),
                    _pre_roll_ids(candidate),
                    prepared_combat.get(index),
                    record_roll,
                )
            )
            handled.add(index)
            continue

        winner_index = conflict_indexes[0]
        roll_ids: list[str] = []
        combat_group = any(item_index in prepared_combat for item_index in conflict_indexes)
        for challenger_index in conflict_indexes[1:]:
            winner = ordered[winner_index]
            challenger = ordered[challenger_index]
            roll = context.random_engine.roll_chance(
                50,
                turn=context.turn,
                label="conflict_resolver.contested",
                severity=(
                    "normal"
                    if combat_group
                    else ("critical" if _is_critical(winner, challenger) else "normal")
                ),
            )
            record_roll(roll)
            roll_ids.append(roll.id)
            if roll.outcome == "failure":
                winner_index = challenger_index
        winner = ordered[winner_index]
        resolved.append(
            _resolve_winner(
                context,
                winner,
                allocate_event_id(),
                [*_pre_roll_ids(winner), *roll_ids],
                prepared_combat.get(winner_index),
                record_roll,
            )
        )
        handled.update(conflict_indexes)
    return resolved


def _prepare_combat(
    context: TurnContext, candidate: Candidate
) -> tuple[CombatPayload, dict[str, int]]:
    combat = CombatPayload.model_validate(candidate.effects["combat"])
    characters = {character.id: character for character in context.bundle.characters}
    attacker = characters.get(combat.attacker)
    defender = characters.get(combat.defender)
    if attacker is None:
        raise ValueError(f"combat character not found: {combat.attacker}")
    if defender is None:
        raise ValueError(f"combat character not found: {combat.defender}")
    if isinstance(candidate, ActionCandidate) and candidate.character_id != combat.attacker:
        raise ValueError("combat attacker must match action candidate character_id")
    if candidate.target_id is not None and candidate.target_id != combat.defender:
        raise ValueError("combat defender must match candidate target_id")
    if "hp" not in defender.stats:
        raise ValueError(f"stat not found for {combat.defender}: hp")

    modifiers: dict[str, int] = {}
    for field_name in ("stat", "skill"):
        name = getattr(combat, field_name)
        if name is None:
            continue
        values = getattr(attacker, f"{field_name}s")
        if name not in values:
            raise ValueError(f"{field_name} not found for {combat.attacker}: {name}")
        modifiers[f"{field_name}:{name}"] = values[name]
    return combat, modifiers


def _resolve_winner(
    context: TurnContext,
    candidate: Candidate,
    event_id: str,
    roll_ids: list[str],
    prepared_combat: tuple[CombatPayload, dict[str, int]] | None,
    record_roll: Callable[[Roll], None],
) -> Event:
    if prepared_combat is None:
        return _event_from_candidate(context, candidate, event_id, roll_ids)
    combat, modifiers = prepared_combat

    roll = context.random_engine.roll_chance(
        combat.target,
        modifiers,
        turn=context.turn,
        label=f"combat:{combat.attacker}:{combat.defender}",
        severity="critical" if combat.life_or_death else "normal",
    )
    record_roll(roll)
    event = _event_from_candidate(context, candidate, event_id, [*roll_ids, roll.id])
    effects: dict[str, Any] = {
        **event.effects,
        "combat": {
            "attacker": combat.attacker,
            "defender": combat.defender,
            "stakes": combat.stakes,
            "result": roll.outcome,
            "damage": combat.damage if roll.outcome == "success" else 0,
            "life_or_death": combat.life_or_death,
        },
    }
    return event.model_copy(update={"type": "combat", "effects": effects})


def _combat_rejection_reason(exc: ValidationError | ValueError) -> str:
    if isinstance(exc, ValidationError):
        reason = exc.errors(include_url=False, include_input=False)[0]["msg"]
    else:
        reason = str(exc)
    return f"invalid combat: {reason}"


def _combat_rejected_event(
    context: TurnContext, candidate: Candidate, event_id: str, reason: str
) -> Event:
    event = _event_from_candidate(context, candidate, event_id)
    return event.model_copy(
        update={
            "type": "combat_rejected",
            "visibility": Visibility.GM_ONLY,
            "known_by": [],
            "effects": {"reason": reason},
        }
    )


def _pre_roll_ids(candidate: Candidate) -> list[str]:
    """Roll id a candidate already carries in ``effects`` (e.g. threat pressure rolls, D121)."""
    roll_id = candidate.effects.get("roll_id")
    return [roll_id] if roll_id else []


def _order_candidates(
    context: TurnContext,
    actions: list[ActionCandidate],
    world_events: list[WorldEventCandidate],
) -> list[Candidate]:
    active = []
    for scene in context.bundle.scenes:
        if scene.status == "active":
            active = scene.active_characters
            break
    order = {character_id: index for index, character_id in enumerate(active)}
    return [
        *sorted(actions, key=lambda item: order.get(item.character_id, 10_000)),
        *world_events,
    ]


def _conflicts(left: Candidate, right: Candidate) -> bool:
    if left is right:
        return True
    left_target = getattr(left, "target_id", None)
    right_target = getattr(right, "target_id", None)
    if left_target is not None and left_target == right_target:
        return True
    return bool(left.effects.get("exclusive") and right.effects.get("exclusive"))


def _is_critical(*candidates: Candidate) -> bool:
    words = ("kill", "death", "dead", "fatal", "殺", "死")
    return any(
        candidate.effects.get("life_or_death")
        or any(word in _candidate_text(candidate).lower() for word in words)
        for candidate in candidates
    )


def _candidate_text(candidate: Candidate) -> str:
    return candidate.action_text if isinstance(candidate, ActionCandidate) else candidate.text


def _event_from_candidate(
    context: TurnContext,
    candidate: Candidate,
    event_id: str,
    roll_ids: list[str] | None = None,
) -> Event:
    if isinstance(candidate, ActionCandidate):
        known_by = [candidate.character_id] if candidate.visibility == Visibility.CHARACTER else []
        return Event(
            id=event_id,
            turn=context.turn,
            type=f"character_{candidate.kind}",
            cause=f"character:{candidate.character_id}:{candidate.source_index or 0}",
            text=candidate.action_text,
            visibility=candidate.visibility,
            known_by=known_by,
            effects={
                **candidate.effects,
                "character_id": candidate.character_id,
                "target_id": candidate.target_id,
            },
            roll_ids=roll_ids or [],
        )
    return Event(
        id=event_id,
        turn=context.turn,
        type=candidate.type,
        cause=candidate.cause,
        text=candidate.text,
        visibility=candidate.visibility,
        known_by=candidate.known_by,
        hidden_from=candidate.hidden_from,
        effects={**candidate.effects, "target_id": candidate.target_id},
        roll_ids=roll_ids or [],
    )
