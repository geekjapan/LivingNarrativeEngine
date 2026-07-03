"""Conflict Resolver slot implementation."""

from collections.abc import Callable

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import ActionCandidate, WorldEventCandidate
from living_narrative.random.models import Roll
from living_narrative.state.models import Event, Visibility

Candidate = ActionCandidate | WorldEventCandidate


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
    resolved: list[Event] = []
    handled: set[int] = set()
    for index, candidate in enumerate(ordered):
        if index in handled:
            continue
        conflict_indexes = [
            other_index
            for other_index, other in enumerate(ordered)
            if other_index >= index and _conflicts(candidate, other)
        ]
        if len(conflict_indexes) <= 1:
            resolved.append(_event_from_candidate(context, candidate, allocate_event_id()))
            handled.add(index)
            continue

        contestants = [ordered[i] for i in conflict_indexes]
        winner = contestants[0]
        roll_ids: list[str] = []
        for challenger in contestants[1:]:
            roll = context.random_engine.roll_chance(
                50,
                turn=context.turn,
                label="conflict_resolver.contested",
                severity="critical" if _is_critical(winner, challenger) else "normal",
            )
            record_roll(roll)
            roll_ids.append(roll.id)
            if roll.outcome == "failure":
                winner = challenger
        resolved.append(_event_from_candidate(context, winner, allocate_event_id(), roll_ids))
        handled.update(conflict_indexes)
    return resolved


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


def _candidate_text(candidate: Candidate) -> str:
    return candidate.action_text if isinstance(candidate, ActionCandidate) else candidate.text
