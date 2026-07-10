"""Builds Narrator input from reader-visible state only (spec-foundation.md §4.3 invariant 2)."""

from typing import Any

from living_narrative.intervention.reveal import must_not_reveal_texts
from living_narrative.narration.models import NarratorContext, OpenThreadInfo
from living_narrative.pipeline.context import TurnContext
from living_narrative.state.models import (
    Event,
    OpenQuestInfo,
    SceneStatus,
    Visibility,
    latest_memory_summary,
)

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
    active_scenes = [scene for scene in context.bundle.scenes if scene.status == SceneStatus.ACTIVE]
    scene_facts = [
        fact
        for scene in active_scenes
        for fact in scene.reader_visible_facts
        if fact not in blocked
    ]
    scene_summary = next((scene.summary for scene in active_scenes if scene.summary), "")
    reader_visible_events = [
        event
        for event in resolved_events
        if is_reader_visible_event(event) and event.text not in blocked
    ]
    # 014: only open (not yet resolved) threads are meta-visible to the Narrator, never to
    # characters (spec §4: characters must not "know" about narrative-ledger bookkeeping).
    open_threads = [
        OpenThreadInfo(id=thread.id, description=thread.description, opened_turn=thread.opened_turn)
        for thread in context.bundle.unresolved_threads
        if thread.status != "resolved"
    ]
    open_quests = [
        OpenQuestInfo(
            id=quest.id,
            title=quest.title,
            status=quest.status,
            objectives=list(quest.objectives),
        )
        for quest in context.bundle.quests
        if quest.status in {"open", "advanced"}
    ]
    # 015: memory-summary due-ness and its input window are both derivable from context alone
    # (turn/world.memory_summary_interval/timeline), so nothing extra needs threading through
    # driver.py's build_narrator_context call.
    interval = context.bundle.world.memory_summary_interval
    memory_summary_due = interval > 0 and context.turn % interval == 0
    summary_window_events: list[str] = []
    if memory_summary_due:
        # Lazy import: mirrors driver.py's D108/D113 rationale — narration must not depend on
        # agents at module import time (agents already depends on narration.models).
        from living_narrative.agents.event_history import load_recent_events

        window_events = load_recent_events(
            context.paths.runs, context.bundle.timeline, max_turns=interval
        )
        summary_window_events = [
            event.text
            for event in window_events
            if is_reader_visible_event(event) and event.text not in blocked
        ]
    memory_summary = latest_memory_summary(context.bundle.memory_summaries)
    return NarratorContext(
        turn=context.turn,
        reader_state_facts=reader_state_facts,
        scene_reader_visible_facts=scene_facts,
        reader_visible_events=reader_visible_events,
        scene_summary=scene_summary,
        open_threads=open_threads,
        open_quests=open_quests,
        memory_summary=memory_summary,
        memory_summary_due=memory_summary_due,
        summary_window_events=summary_window_events,
    )
