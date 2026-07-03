"""Builds Narrator input from reader-visible state only (spec-foundation.md §4.3 invariant 2)."""

from typing import Any

from living_narrative.intervention.reveal import must_not_reveal_texts
from living_narrative.narration.models import NarratorContext
from living_narrative.pipeline.context import TurnContext
from living_narrative.state.models import Event, SceneStatus, Visibility

_READER_VISIBLE = (Visibility.READER, Visibility.CANON)


def is_reader_visible_event(event: Event) -> bool:
    """§4.2: reader-facing content must be canon or reader-tagged."""
    return event.visibility in _READER_VISIBLE


def build_narrator_context(
    context: TurnContext,
    resolved_events: list[Event],
    interventions: list[dict[str, Any]] = (),
) -> NarratorContext:
    blocked = must_not_reveal_texts(context, interventions)
    reader_state_facts = [entry.text for entry in context.bundle.reader_state]
    scene_facts = [
        fact
        for scene in context.bundle.scenes
        if scene.status == SceneStatus.ACTIVE
        for fact in scene.reader_visible_facts
        if fact not in blocked
    ]
    reader_visible_events = [
        event
        for event in resolved_events
        if is_reader_visible_event(event) and event.text not in blocked
    ]
    return NarratorContext(
        turn=context.turn,
        reader_state_facts=reader_state_facts,
        scene_reader_visible_facts=scene_facts,
        reader_visible_events=reader_visible_events,
    )
