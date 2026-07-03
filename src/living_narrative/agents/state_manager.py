"""State Manager BuildDiff slot implementation."""

from typing import Any

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import BuildDiffOutput, RejectedChange
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Event, Visibility


def build_state_diff(
    context: TurnContext,
    resolved_events: list[Event],
    interventions: list[dict[str, Any]],
) -> BuildDiffOutput:
    must_not_reveal = {
        item.get("fact_id") or item.get("target_id")
        for item in interventions
        if item.get("type") == "reveal_control" and item.get("mode") == "must-not-reveal"
    }
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    for event in resolved_events:
        for candidate in _changes_for_event(context, event):
            if candidate.source_event is None:
                rejected.append(_reject(candidate, "missing source_event"))
            elif _blocked_reveal(candidate, must_not_reveal):
                rejected.append(_reject(candidate, "blocked by reveal_control must-not-reveal"))
            elif not _valid_target(context, candidate):
                rejected.append(_reject(candidate, "target id not found in current state"))
            else:
                changes.append(candidate)
    return BuildDiffOutput(
        diff=StateDiff(id=f"diff_{context.turn:04d}", turn=context.turn, changes=changes),
        rejected_changes=rejected,
    )


def _changes_for_event(context: TurnContext, event: Event) -> list[StateDiffChange]:
    changes = []
    character_id = event.effects.get("character_id") or event.effects.get("target_id")
    scene_id = event.effects.get("scene_id") or event.effects.get("target_id")
    if event.effects.get("status") == "dead" or event.type == "character_death":
        changes.append(
            StateDiffChange(
                target="character",
                id=character_id,
                op="set",
                path="status",
                value="dead",
                visibility=Visibility.CANON,
                source_event=event.id,
            )
        )
    if event.effects.get("scene_status") == "ended" or event.type == "scene_end":
        changes.append(
            StateDiffChange(
                target="scene",
                id=scene_id or _active_scene_id(context),
                op="set",
                path="status",
                value="ended",
                visibility=Visibility.CANON,
                source_event=event.id,
            )
        )
    reveal_text = event.effects.get("reveal_text")
    if reveal_text:
        changes.append(
            StateDiffChange(
                target="reader_state",
                op="add",
                path="",
                value={
                    "id": f"reader_state_{context.turn:04d}",
                    "text": reveal_text,
                    "established_turn": context.turn,
                    "source_event": event.id,
                    "disclosed_turn": context.turn,
                },
                visibility=Visibility.READER,
                source_event=event.id,
            )
        )
    return changes


def _blocked_reveal(change: StateDiffChange, must_not_reveal: set[Any]) -> bool:
    if change.target != "reader_state":
        return False
    value = change.value if isinstance(change.value, dict) else {}
    return bool({value.get("id"), value.get("fact_id"), value.get("text")} & must_not_reveal)


def _valid_target(context: TurnContext, change: StateDiffChange) -> bool:
    if change.target == "character":
        return any(character.id == change.id for character in context.bundle.characters)
    if change.target == "scene":
        return any(scene.id == change.id for scene in context.bundle.scenes)
    return True


def _active_scene_id(context: TurnContext) -> str | None:
    for scene in context.bundle.scenes:
        if scene.status == "active":
            return scene.id
    return None


def _reject(change: StateDiffChange, reason: str) -> RejectedChange:
    return RejectedChange(change=change, reason=reason)
