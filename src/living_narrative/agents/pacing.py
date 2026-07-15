"""Shared narrative-stall detection (Issue 011).

A "stall" is `pacing.stall_window` consecutive turns with no advancement signal: no new
threat stage, no scene transition, no new canon/reader-state fact. `threat_pressure` and
`background_event` fire every turn by design and are deliberately excluded, or every turn
would look like progress.
"""

from living_narrative.agents.event_history import load_recent_events
from living_narrative.pipeline.context import TurnContext
from living_narrative.state.models import Event

ADVANCEMENT_EVENT_TYPES = frozenset({"threat_stage", "scene_end"})


_THREAD_ADVANCEMENT_ACTIONS = frozenset({"advance", "resolve"})


def is_advancement_event(event: Event) -> bool:
    """Whether ``event`` counts as narrative progress for stall detection.

    014: a thread ``advance``/``resolve`` counts as progress; ``open`` does not (stacking a
    new mystery isn't forward motion on its own).
    """
    if event.type in ADVANCEMENT_EVENT_TYPES or "scene_transition" in event.effects:
        return True
    if event.type == "thread_update":
        return event.effects.get("action") in _THREAD_ADVANCEMENT_ACTIONS
    if event.type == "action_outcome":
        return bool(event.effects.get("accepted") and event.effects.get("advancement"))
    if event.type == "combat":
        combat = event.effects.get("combat")
        return isinstance(combat, dict) and combat.get("result") == "success"
    return False


def detect_stall(context: TurnContext) -> int | None:
    """Number of stalled turns (``pacing.stall_window``) if the last window of turns had no
    advancement signal, else ``None`` (also ``None`` when the feature is off, i.e.
    ``stall_window <= 0``, or when there aren't yet ``stall_window`` prior turns to judge).
    """
    window = context.bundle.world.pacing.stall_window
    if window <= 0 or context.turn <= window:
        return None

    lower = context.turn - window
    upper = context.turn - 1

    past_events = load_recent_events(context.paths.runs, context.bundle.timeline, max_turns=window)
    if any(is_advancement_event(event) for event in past_events):
        return None
    if any(lower <= entry.established_turn <= upper for entry in context.bundle.reader_state):
        return None
    if any(lower <= entry.established_turn <= upper for entry in context.bundle.canon):
        return None
    return window
