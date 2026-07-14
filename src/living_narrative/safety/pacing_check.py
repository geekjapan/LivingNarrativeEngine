"""Pacing/stall checker (Issue 011): warns, never blocks, when the story has stalled."""

from living_narrative.agents.pacing import detect_stall, is_advancement_event
from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.registry import Finding
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event


def pacing_checker(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[Finding]:
    if any(event.type == "pacing_exhausted" for event in resolved_events):
        return [
            Finding(
                checker="pacing_check",
                severity="error",
                message="作者定義の進展手段が尽きた(pacing_exhausted)",
            )
        ]
    # The stall is already being broken this turn (a new stage/scene-transition just
    # resolved) -- no need to warn about it.
    if any(is_advancement_event(event) for event in resolved_events):
        return []
    stalled_turns = detect_stall(context)
    if stalled_turns is None:
        return []
    return [
        Finding(
            checker="pacing_check",
            severity="warn",
            message=f"物語が{stalled_turns}ターン前進していない(新シーン・新事実・脅威段階なし)",
        )
    ]
