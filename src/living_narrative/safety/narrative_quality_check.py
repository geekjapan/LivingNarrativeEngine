"""Opt-in, reader-safe mechanical checks for narration quality candidates."""

from living_narrative.agents.event_history import load_recent_events
from living_narrative.agents.pacing import is_advancement_event
from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.registry import Finding
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event, Visibility


def narrative_quality_checker(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[Finding]:
    """Return fixed-code errors only; never expose candidate prose in findings."""
    del diff_candidate

    policy = context.project.narrative_quality
    if not policy.enabled:
        return []

    if (
        policy.minimum_narration_characters > 0
        and len(narration_text) < policy.minimum_narration_characters
    ):
        return [
            Finding(
                checker="narrative_quality",
                severity="error",
                message="narration_too_short",
            )
        ]

    maximum_stalls = policy.maximum_consecutive_stall_turns
    if maximum_stalls is not None and _exceeds_stall_limit(
        context, resolved_events, maximum_stalls
    ):
        return [
            Finding(
                checker="narrative_quality",
                severity="error",
                message="consecutive_stall_limit_exceeded",
            )
        ]

    return []


def _exceeds_stall_limit(
    context: TurnContext, resolved_events: list[Event], maximum_stalls: int
) -> bool:
    """Whether the current candidate exceeds a configured sequence of no advancement."""
    if any(
        event.visibility == Visibility.READER and is_advancement_event(event)
        for event in resolved_events
    ):
        return False
    if context.turn <= maximum_stalls:
        return False

    lower = context.turn - maximum_stalls
    upper = context.turn - 1
    past_events = load_recent_events(
        context.paths.runs, context.bundle.timeline, max_turns=maximum_stalls
    )
    if any(
        event.visibility == Visibility.READER and is_advancement_event(event)
        for event in past_events
    ):
        return False
    return not any(
        lower <= entry.established_turn <= upper for entry in context.bundle.reader_state
    )
