"""Conflict Resolver slot implementation."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from living_narrative.agents.affordance_policy import (
    affordance_prerequisites_met,
    affordance_visible_to_character,
)
from living_narrative.agents.pacing import detect_stall
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
    used_affordances: set[str] = set()
    normal_outcome_succeeded = False
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
            winner_events = _resolve_winner(
                context,
                candidate,
                allocate_event_id(),
                _pre_roll_ids(candidate),
                prepared_combat.get(index),
                record_roll,
                allocate_event_id,
                used_affordances,
            )
            resolved.extend(winner_events)
            normal_outcome_succeeded = normal_outcome_succeeded or any(
                _is_successful_outcome_event(event) for event in winner_events
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
        winner_events = _resolve_winner(
            context,
            winner,
            allocate_event_id(),
            [*_pre_roll_ids(winner), *roll_ids],
            prepared_combat.get(winner_index),
            record_roll,
            allocate_event_id,
            used_affordances,
        )
        resolved.extend(winner_events)
        normal_outcome_succeeded = normal_outcome_succeeded or any(
            _is_successful_outcome_event(event) for event in winner_events
        )
        handled.update(conflict_indexes)
    if not normal_outcome_succeeded and detect_stall(context) is not None:
        fallback_events = _resolve_fallback(
            context, allocate_event_id, record_roll, used_affordances
        )
        resolved.extend(fallback_events)
    return resolved


def _prepare_combat(
    context: TurnContext, candidate: Candidate
) -> tuple[CombatPayload, dict[str, int]]:
    combat = CombatPayload.model_validate(candidate.effects["combat"])
    if isinstance(candidate, ActionCandidate) and candidate.intent is not None:
        raise ValueError("candidate cannot declare both combat and a structured intent")
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
    attacker_scene = next(
        (
            scene
            for scene in context.bundle.scenes
            if scene.status == "active" and combat.attacker in scene.active_characters
        ),
        None,
    )
    if attacker_scene is None or combat.defender not in attacker_scene.active_characters:
        raise ValueError(f"combat defender is outside active scene: {combat.defender}")
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
    allocate_event_id: Callable[[], str],
    used_affordances: set[str] | None = None,
) -> list[Event]:
    if prepared_combat is None:
        event = _event_from_candidate(context, candidate, event_id, roll_ids)
        if isinstance(candidate, ActionCandidate) and candidate.intent is not None:
            return _resolve_action_intent(
                context,
                candidate,
                event,
                allocate_event_id=allocate_event_id,
                record_roll=record_roll,
                used_affordances=used_affordances if used_affordances is not None else set(),
            )
        return [event]
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
    return [event.model_copy(update={"type": "combat", "effects": effects})]


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
                **(
                    {"combat": candidate.effects["combat"]} if "combat" in candidate.effects else {}
                ),
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


def _resolve_action_intent(
    context: TurnContext,
    candidate: ActionCandidate,
    base_event: Event,
    allocate_event_id: Callable[[], str],
    record_roll: Callable[[Roll], None],
    used_affordances: set[str],
    allow_fallback: bool = False,
) -> list[Event]:
    """Resolve a structured intent against the active authored affordance ledger."""
    intent = candidate.intent
    if intent is None:
        return [base_event]
    if (
        getattr(
            next(
                (
                    affordance
                    for scene in context.bundle.scenes
                    for affordance in getattr(scene, "affordances", [])
                    if getattr(affordance, "id", None) == intent.affordance_id
                ),
                None,
            ),
            "fallback_only",
            False,
        )
        and not allow_fallback
    ):
        return [base_event, _intent_rejected_event(context, allocate_event_id(), "fallback_only")]
    affordance, reason = _find_eligible_affordance(
        context, candidate.character_id, intent.affordance_id
    )
    if reason is not None or affordance is None:
        return [
            base_event,
            _intent_rejected_event(context, allocate_event_id(), reason or "unknown_affordance"),
        ]
    affordance_id = affordance.id
    if affordance_id in used_affordances and (
        affordance.recurrence == "once" or affordance.exclusive
    ):
        return [
            base_event,
            _intent_rejected_event(context, allocate_event_id(), "already_triggered"),
        ]
    # Once/exclusive declarations are per-turn exclusive after the first valid winner;
    # a failed chance still consumes the turn's attempt, keeping resolution deterministic.
    if affordance.recurrence == "once" or affordance.exclusive:
        used_affordances.add(affordance_id)
    if affordance.recurrence == "once" and affordance.used_event_ids:
        return [base_event, _intent_rejected_event(context, allocate_event_id(), "already_used")]

    roll_ids = list(base_event.roll_ids)
    if affordance.success_chance < 100:
        roll = context.random_engine.roll_chance(
            affordance.success_chance,
            turn=context.turn,
            label=f"action_outcome:{affordance_id}",
        )
        record_roll(roll)
        roll_ids.append(roll.id)
        if roll.outcome != "success":
            return [
                base_event,
                _intent_rejected_event(context, allocate_event_id(), "chance_failed", roll_ids),
            ]

    declarations = [_dump_outcome(item) for item in affordance.outcomes]
    if not any(_outcome_would_change_state(context, item) for item in declarations):
        return [base_event, _intent_rejected_event(context, allocate_event_id(), "no_effect")]
    advancement = any(_outcome_is_advancement(context, declaration) for declaration in declarations)
    outcome_visibility = _outcome_visibility(affordance.visibility, declarations)
    payload = {
        "affordance_id": affordance_id,
        "character_id": candidate.character_id,
        "outcomes": declarations,
        "consumption": {
            "recurrence": affordance.recurrence,
            "exclusive": affordance.exclusive,
            "fallback": allow_fallback,
        },
    }
    outcome_event = Event(
        id=allocate_event_id(),
        turn=context.turn,
        type="action_outcome",
        cause=f"action:{candidate.character_id}:{affordance_id}",
        text=affordance.text,
        visibility=outcome_visibility,
        known_by=([candidate.character_id] if outcome_visibility == Visibility.CHARACTER else []),
        effects={"action_outcome": payload, "accepted": True, "advancement": advancement},
        roll_ids=roll_ids,
    )
    return [base_event, outcome_event]


def _find_eligible_affordance(
    context: TurnContext, character_id: str, affordance_id: str
) -> tuple[Any | None, str | None]:
    for scene in context.bundle.scenes:
        status = scene.status.value if hasattr(scene.status, "value") else scene.status
        if status != "active":
            continue
        if character_id not in scene.active_characters:
            continue
        for affordance in getattr(scene, "affordances", []):
            if affordance.id != affordance_id:
                continue
            if not affordance_visible_to_character(affordance, character_id):
                return None, "not_visible"
            if affordance.actor_ids and character_id not in affordance.actor_ids:
                return None, "actor_not_allowed"
            if not affordance_prerequisites_met(context.bundle, affordance.prerequisites):
                return None, "prerequisites_unmet"
            if affordance.recurrence == "once" and affordance.used_event_ids:
                return None, "already_used"
            return affordance, None
    return None, "unknown_affordance"


def _dump_outcome(outcome: Any) -> dict[str, Any]:
    return outcome.model_dump(mode="json") if hasattr(outcome, "model_dump") else dict(outcome)


def _outcome_visibility(
    affordance_visibility: Visibility, declarations: list[dict[str, Any]]
) -> Visibility:
    visibilities = [Visibility(item["visibility"]) for item in declarations]
    if affordance_visibility == Visibility.GM_ONLY or any(
        item == Visibility.GM_ONLY for item in visibilities
    ):
        return Visibility.GM_ONLY
    if affordance_visibility == Visibility.CHARACTER or any(
        item == Visibility.CHARACTER for item in visibilities
    ):
        return Visibility.CHARACTER
    if affordance_visibility == Visibility.SCENE or any(
        item == Visibility.SCENE for item in visibilities
    ):
        return Visibility.SCENE
    return Visibility.READER


def _outcome_is_advancement(context: TurnContext, outcome: dict[str, Any]) -> bool:
    target, op, path, value = (
        outcome.get("target"),
        outcome.get("op"),
        outcome.get("path", ""),
        outcome.get("value"),
    )
    if outcome.get("visibility") not in {Visibility.READER.value, Visibility.CANON.value}:
        return False
    if not _outcome_would_change_state(context, outcome):
        return False
    if target in {"canon", "reader_state"}:
        return op == "add" and path == ""
    if target == "threads":
        return path == "status" and op == "set" and value in {"advanced", "resolved"}
    if target == "quests":
        return path == "status" and op == "set" and value in {"advanced", "resolved"}
    if target == "scene":
        return path == "status" and op == "set" and value in {"active", "ended"}
    if target == "character":
        return path == "status" and op == "set" and value in {"dead", "missing"}
    return False


def _outcome_would_change_state(context: TurnContext, outcome: dict[str, Any]) -> bool:
    target, op, path, value, item_id = (
        outcome.get("target"),
        outcome.get("op"),
        outcome.get("path", ""),
        outcome.get("value"),
        outcome.get("id"),
    )
    if target == "scene":
        current = next((item for item in context.bundle.scenes if item.id == item_id), None)
    elif target == "character":
        current = next((item for item in context.bundle.characters if item.id == item_id), None)
    elif target == "threads":
        current = next(
            (item for item in context.bundle.unresolved_threads if item.id == item_id), None
        )
    elif target == "quests":
        current = next((item for item in context.bundle.quests if item.id == item_id), None)
    elif target == "canon":
        current = next((item for item in context.bundle.canon if item.id == item_id), None)
    elif target == "reader_state":
        current = next((item for item in context.bundle.reader_state if item.id == item_id), None)
    else:
        return False
    if not path and op == "add" and isinstance(value, dict):
        collection = {
            "threads": context.bundle.unresolved_threads,
            "quests": context.bundle.quests,
            "canon": context.bundle.canon,
            "reader_state": context.bundle.reader_state,
        }.get(target, [])
        return not any(getattr(item, "id", None) == value.get("id") for item in collection)
    if current is None:
        return False
    for part in path.split(".") if path else []:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return False
    if op == "set":
        return current != value
    if op == "delta" and isinstance(current, int):
        return max(0, min(100, current + value)) != current
    if op == "add" and isinstance(current, list):
        return value not in current
    return True


def _intent_rejected_event(
    context: TurnContext,
    event_id: str,
    reason: str,
    roll_ids: list[str] | None = None,
) -> Event:
    return Event(
        id=event_id,
        turn=context.turn,
        type="action_intent_rejected",
        cause="action_intent",
        text="構造化された行動は成立しなかった。",
        visibility=Visibility.GM_ONLY,
        effects={"reason": reason},
        roll_ids=roll_ids or [],
    )


def _is_successful_outcome_event(event: Event) -> bool:
    if event.type == "action_outcome":
        return bool(event.effects.get("accepted"))
    combat = event.effects.get("combat")
    return event.type == "combat" and isinstance(combat, dict) and combat.get("result") == "success"


def _resolve_fallback_for_actors(
    context: TurnContext,
    affordance: Any,
    actor_ids: list[str],
    allocate_event_id: Callable[[], str],
    record_roll: Callable[[Roll], None],
    used_affordances: set[str],
) -> list[Event] | None:
    """Try each actor eligible for ``affordance`` in turn; an actor-specific visibility/scope
    rejection moves on to the next actor instead of stalling the whole fallback search."""
    for actor_id in actor_ids:
        candidate = ActionCandidate(
            character_id=actor_id,
            action_text=affordance.text,
            visibility=affordance.visibility,
            intent={"affordance_id": affordance.id},
        )
        base = _event_from_candidate(context, candidate, allocate_event_id())
        events = _resolve_action_intent(
            context,
            candidate,
            base,
            allocate_event_id,
            record_roll,
            used_affordances,
            allow_fallback=True,
        )
        rejection = next(
            (event for event in events if event.type == "action_intent_rejected"), None
        )
        if rejection is not None and rejection.effects.get("reason") in {
            "not_visible",
            "actor_not_allowed",
        }:
            continue
        return events
    return None


def _resolve_fallback(
    context: TurnContext,
    allocate_event_id: Callable[[], str],
    record_roll: Callable[[Roll], None],
    used_affordances: set[str],
) -> list[Event]:
    for scene in context.bundle.scenes:
        status = scene.status.value if hasattr(scene.status, "value") else scene.status
        if status != "active" or not scene.fallback_affordance_ids:
            continue
        affordances = {item.id: item for item in scene.affordances}
        for affordance_id in scene.fallback_affordance_ids:
            affordance = affordances.get(affordance_id)
            if affordance is None or affordance.id in used_affordances:
                continue
            actor_ids = [
                item
                for item in scene.active_characters
                if not affordance.actor_ids or item in affordance.actor_ids
            ]
            if not actor_ids or affordance.recurrence == "once" and affordance.used_event_ids:
                continue
            if not affordance_prerequisites_met(context.bundle, affordance.prerequisites):
                continue
            if not any(
                _outcome_is_advancement(context, _dump_outcome(item))
                for item in affordance.outcomes
            ):
                continue
            result = _resolve_fallback_for_actors(
                context,
                affordance,
                actor_ids,
                allocate_event_id,
                record_roll,
                used_affordances,
            )
            if result is not None:
                return result
    if any(
        (scene.status.value if hasattr(scene.status, "value") else scene.status) == "active"
        and scene.pacing_terminal
        for scene in context.bundle.scenes
    ):
        return []
    return [
        Event(
            id=allocate_event_id(),
            turn=context.turn,
            type="pacing_exhausted",
            cause="pacing",
            text="作者定義の進展手段が利用できない。",
            visibility=Visibility.GM_ONLY,
            effects={"reason": "no_eligible_fallback"},
        )
    ]
