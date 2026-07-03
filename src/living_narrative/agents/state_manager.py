"""State Manager BuildDiff slot implementation."""

from collections.abc import Callable
from typing import Any

from living_narrative.intervention.reveal import must_not_reveal_texts, reveal_now_sources
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import BuildDiffOutput, RejectedChange
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Event, Visibility

# canon_edit/hidden_truth_edit (spec.md Requirement "Type別ルーティング"): a state diff target
# per type, keyed by the collection this intervention type adds to.
_EDIT_TARGETS = {"canon_edit": "canon", "hidden_truth_edit": "gm_vault"}


def _default_event_id_allocator() -> Callable[[], str]:
    """Fallback used only when a caller (e.g. a pre-existing unit test) doesn't supply one."""
    counter = [9000]

    def allocate() -> str:
        counter[0] += 1
        return f"event_{counter[0]:04d}"

    return allocate


def build_state_diff(
    context: TurnContext,
    resolved_events: list[Event],
    interventions: list[dict[str, Any]],
    allocate_event_id: Callable[[], str] | None = None,
) -> BuildDiffOutput:
    allocate_event_id = allocate_event_id or _default_event_id_allocator()
    must_not_reveal = must_not_reveal_texts(context, interventions)
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    synthetic_events: list[Event] = []

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

    edit_counters: dict[str, int] = {}
    for item in interventions:
        target = _EDIT_TARGETS.get(item.get("type"))
        if target is None:
            continue
        edit_counters[target] = edit_counters.get(target, 0) + 1
        event, change = _synthetic_edit_change(
            context, item, target, edit_counters[target], allocate_event_id
        )
        synthetic_events.append(event)
        changes.append(change)

    reveal_now_index = 0
    for item, entry in reveal_now_sources(context, interventions):
        if any(existing.text == entry.text for existing in context.bundle.reader_state):
            continue
        reveal_now_index += 1
        event, change = _reveal_now_change(
            context, item, entry, reveal_now_index, allocate_event_id
        )
        synthetic_events.append(event)
        changes.append(change)

    return BuildDiffOutput(
        diff=StateDiff(id=f"diff_{context.turn:04d}", turn=context.turn, changes=changes),
        rejected_changes=rejected,
        synthetic_events=synthetic_events,
    )


def _synthetic_edit_change(
    context: TurnContext,
    item: dict[str, Any],
    target: str,
    index: int,
    allocate_event_id: Callable[[], str],
) -> tuple[Event, StateDiffChange]:
    event = Event(
        id=allocate_event_id(),
        turn=context.turn,
        type=item["type"],
        cause=f"intervention:{item['id']}",
        text=item.get("content", ""),
        visibility=Visibility(item["visibility"]),
    )
    entry_id = f"{target}_{context.turn:04d}{index:02d}"
    value: dict[str, Any] = {"id": entry_id, "text": item.get("content", "")}
    if target == "canon":
        value["established_turn"] = context.turn
        value["source_event"] = event.id
    else:
        value["reveal_condition"] = (item.get("constraints") or {}).get("reveal_condition")
    change = StateDiffChange(
        target=target,
        op="add",
        path="",
        value=value,
        visibility=Visibility(item["visibility"]),
        source_event=event.id,
    )
    return event, change


def _reveal_now_change(
    context: TurnContext,
    item: dict[str, Any],
    entry: Any,
    index: int,
    allocate_event_id: Callable[[], str],
) -> tuple[Event, StateDiffChange]:
    event = Event(
        id=allocate_event_id(),
        turn=context.turn,
        type="reveal_control",
        cause=f"intervention:{item['id']}",
        text=entry.text,
        visibility=Visibility.READER,
    )
    change = StateDiffChange(
        target="reader_state",
        op="add",
        path="",
        value={
            "id": f"reader_state_{context.turn:04d}{index:02d}",
            "text": entry.text,
            "established_turn": context.turn,
            "source_event": event.id,
            "disclosed_turn": context.turn,
        },
        visibility=Visibility.READER,
        source_event=event.id,
    )
    return event, change


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
