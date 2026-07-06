"""State Manager BuildDiff slot implementation."""

from collections.abc import Callable
from typing import Any

from living_narrative.agents.models import CharacterAgentOutput
from living_narrative.intervention.reveal import must_not_reveal_texts, reveal_now_sources
from living_narrative.narration.models import ThreadUpdateCandidate
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import BuildDiffOutput, RejectedChange
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import (
    CharacterId,
    CharacterStatus,
    Event,
    SceneStatus,
    TimelineEntry,
    Visibility,
)

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
    character_outputs: list[tuple[CharacterId, CharacterAgentOutput]] | None = None,
    scene_summary_update: str | None = None,
    thread_updates: list[ThreadUpdateCandidate] | None = None,
    memory_summary_update: str | None = None,
) -> BuildDiffOutput:
    allocate_event_id = allocate_event_id or _default_event_id_allocator()
    must_not_reveal = must_not_reveal_texts(context, interventions)
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    synthetic_events: list[Event] = []

    for event in resolved_events:
        for candidate in _changes_for_event(context, event):
            transition_reason = _invalid_scene_transition_reason(context, candidate)
            if candidate.source_event is None:
                rejected.append(_reject(candidate, "missing source_event"))
            elif _blocked_reveal(candidate, must_not_reveal):
                rejected.append(_reject(candidate, "blocked by reveal_control must-not-reveal"))
            elif transition_reason is not None:
                rejected.append(_reject(candidate, transition_reason))
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

    for character_id, output in character_outputs or []:
        output_changes, output_rejected = _character_output_changes(context, character_id, output)
        changes.extend(output_changes)
        rejected.extend(output_rejected)

    # 010: ベースライン減衰(エンジン側・決定論)。rate 0 またはbaseline未定義ならno-op。
    changes.extend(_emotion_decay_changes(context))

    # 007: ナレーターが書いた場面の現在状況更新をsetに変換(leak-safe by construction: ADR-0003)。
    if scene_summary_update:
        scene_id = _active_scene_id(context)
        if scene_id is not None:
            changes.append(
                StateDiffChange(
                    target="scene",
                    id=scene_id,
                    op="set",
                    path="summary",
                    value=scene_summary_update,
                    visibility=Visibility.SCENE,
                )
            )

    # 014: ナレーターのthread_updatesをthreadsコレクションへの変換(leak-safe by construction:
    # 007と同型 — ナレーターはreader可視情報しか見ていないので起票内容も漏洩しない)。
    thread_changes, thread_rejected, thread_events = _thread_update_changes(
        context, thread_updates or [], resolved_events, allocate_event_id
    )
    changes.extend(thread_changes)
    rejected.extend(thread_rejected)
    synthetic_events.extend(thread_events)

    # 015: ナレーターのmemory_summary_updateをmemoryコレクションへのadd diffに変換(leak-safe:
    # 007/014と同根拠 — ナレーターはreader可視情報しか見ていないので要約内容も漏洩しない)。
    if memory_summary_update:
        changes.append(
            StateDiffChange(
                target="memory",
                op="add",
                path="",
                value={
                    "id": f"memory_{context.turn:04d}",
                    "up_to_turn": context.turn,
                    "text": memory_summary_update,
                },
                visibility=Visibility.READER,
            )
        )

    timeline_event_ids = [event.id for event in resolved_events] + [
        event.id for event in synthetic_events
    ]
    if timeline_event_ids:
        changes.append(
            StateDiffChange(
                target="timeline",
                op="add",
                path="",
                value=TimelineEntry(turn=context.turn, event_ids=timeline_event_ids).model_dump(
                    mode="json"
                ),
                visibility=Visibility.CANON,
            )
        )

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


def _character_output_changes(
    context: TurnContext, character_id: CharacterId, output: CharacterAgentOutput
) -> tuple[list[StateDiffChange], list[RejectedChange]]:
    character = next((c for c in context.bundle.characters if c.id == character_id), None)
    known_emotions = set(character.emotions) if character else set()
    changes = []
    rejected = []
    for emotion_delta in output.emotion_deltas:
        change = StateDiffChange(
            target="character",
            id=character_id,
            op="delta",
            path=f"emotions.{emotion_delta.emotion}",
            value=emotion_delta.delta,
            visibility=emotion_delta.visibility,
        )
        # delta opは既存パス必須(StateDiffError回避): キャラに無い感情キーは棄却
        if emotion_delta.emotion not in known_emotions:
            rejected.append(_reject(change, "unknown emotion key for character"))
        else:
            changes.append(change)
    for goal_update in output.goal_updates:
        changes.append(
            StateDiffChange(
                target="character",
                id=character_id,
                op="add",
                path=f"goals.{goal_update.goal_kind}",
                value=goal_update.content,
                visibility=goal_update.visibility,
            )
        )
    known_relationship_pairs = {
        (relationship.from_, relationship.to) for relationship in context.bundle.relationships
    }
    for relationship_update in output.relationship_updates:
        # 013: asymmetric by design (D116 composite key) — only the actor's own from-side
        # view updates; no self-target and the pair must already exist in current state.
        # Self-target is checked before building the relationship-target StateDiffChange
        # because its id validator rejects "<x>__<x>" outright (can't even construct one
        # to report as rejected).
        if relationship_update.to == character_id:
            stub = StateDiffChange(
                target="character",
                id=character_id,
                op="delta",
                path=f"relationships.{relationship_update.to}.{relationship_update.dimension}",
                value=relationship_update.delta,
                visibility=Visibility.CHARACTER,
            )
            rejected.append(_reject(stub, "relationship update targets self"))
            continue
        change = StateDiffChange(
            target="relationship",
            id=f"{character_id}__{relationship_update.to}",
            op="delta",
            path=relationship_update.dimension,
            value=relationship_update.delta,
            visibility=Visibility.CHARACTER,
        )
        if (character_id, relationship_update.to) not in known_relationship_pairs:
            rejected.append(_reject(change, "relationship pair not found"))
        else:
            changes.append(change)
    return changes, rejected


def _emotion_decay_changes(context: TurnContext) -> list[StateDiffChange]:
    """Issue 010: every ALIVE character's emotions drift toward ``emotions_baseline`` by up
    to ``world.emotion_decay_per_turn`` per turn, in whichever direction closes the gap,
    landing exactly on the baseline instead of overshooting it. A character with no baseline
    for a given emotion (or rate 0) is left untouched (back-compat)."""
    rate = context.bundle.world.emotion_decay_per_turn
    if rate <= 0:
        return []
    changes = []
    for character in context.bundle.characters:
        if character.status != CharacterStatus.ALIVE:
            continue
        for emotion in sorted(character.emotions_baseline):
            if emotion not in character.emotions:
                continue
            distance = character.emotions_baseline[emotion] - character.emotions[emotion]
            if distance == 0:
                continue
            step = min(rate, abs(distance))
            delta = step if distance > 0 else -step
            changes.append(
                StateDiffChange(
                    target="character",
                    id=character.id,
                    op="delta",
                    path=f"emotions.{emotion}",
                    value=delta,
                    visibility=Visibility.CHARACTER,
                )
            )
    return changes


def _thread_update_changes(
    context: TurnContext,
    thread_updates: list[ThreadUpdateCandidate],
    resolved_events: list[Event],
    allocate_event_id: Callable[[], str],
) -> tuple[list[StateDiffChange], list[RejectedChange], list[Event]]:
    """Issue 014: convert narrator ``thread_updates`` into ``threads``-target diff changes.

    Each accepted update also emits a synthetic ``gm_only`` ``thread_update`` event (mirroring
    ``_synthetic_edit_change``) so ``pacing.detect_stall`` can see advance/resolve as narrative
    progress (open does not count — see ``agents/pacing.py``). Rejected updates never produce
    an event: unknown ``thread_id``, an ``advance``/``resolve`` on an already-resolved thread,
    and an ``open`` missing ``description`` are all declined without side effects.
    """
    known_threads = {thread.id: thread for thread in context.bundle.unresolved_threads}
    this_turn_event_ids = [event.id for event in resolved_events]
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    events: list[Event] = []
    open_index = 0

    for update in thread_updates:
        if update.action == "open":
            if not update.description:
                stub = StateDiffChange(
                    target="threads", op="add", path="", value={}, visibility=Visibility.GM_ONLY
                )
                rejected.append(_reject(stub, "open thread update missing description"))
                continue
            open_index += 1
            thread_id = f"thread_{context.turn:04d}{open_index:02d}"
            event = Event(
                id=allocate_event_id(),
                turn=context.turn,
                type="thread_update",
                cause="narrator",
                text=update.description,
                visibility=Visibility.GM_ONLY,
                effects={"action": "open", "thread_id": thread_id},
            )
            events.append(event)
            changes.append(
                StateDiffChange(
                    target="threads",
                    op="add",
                    path="",
                    value={
                        "id": thread_id,
                        "description": update.description,
                        "status": "open",
                        "related_event_ids": [],
                        "notes": [],
                        "opened_turn": context.turn,
                    },
                    visibility=Visibility.GM_ONLY,
                    source_event=event.id,
                )
            )
            continue

        thread = known_threads.get(update.thread_id or "")
        if thread is None:
            stub = StateDiffChange(
                target="threads",
                op="set" if update.action == "resolve" else "add",
                path="status" if update.action == "resolve" else "notes",
                id=update.thread_id,
                value=update.note if update.action == "advance" else "resolved",
                visibility=Visibility.GM_ONLY,
            )
            rejected.append(_reject(stub, f"unknown thread_id: {update.thread_id!r}"))
            continue
        if thread.status == "resolved":
            stub = StateDiffChange(
                target="threads",
                op="set" if update.action == "resolve" else "add",
                path="status" if update.action == "resolve" else "notes",
                id=thread.id,
                value=update.note if update.action == "advance" else "resolved",
                visibility=Visibility.GM_ONLY,
            )
            rejected.append(_reject(stub, f"thread already resolved: {thread.id}"))
            continue

        if update.action == "advance":
            event = Event(
                id=allocate_event_id(),
                turn=context.turn,
                type="thread_update",
                cause="narrator",
                text=update.note or thread.description,
                visibility=Visibility.GM_ONLY,
                effects={"action": "advance", "thread_id": thread.id},
            )
            events.append(event)
            if update.note:
                changes.append(
                    StateDiffChange(
                        target="threads",
                        id=thread.id,
                        op="add",
                        path="notes",
                        value=update.note,
                        visibility=Visibility.GM_ONLY,
                        source_event=event.id,
                    )
                )
            for event_id in this_turn_event_ids:
                changes.append(
                    StateDiffChange(
                        target="threads",
                        id=thread.id,
                        op="add",
                        path="related_event_ids",
                        value=event_id,
                        visibility=Visibility.GM_ONLY,
                        source_event=event.id,
                    )
                )
        else:  # resolve
            event = Event(
                id=allocate_event_id(),
                turn=context.turn,
                type="thread_update",
                cause="narrator",
                text=thread.description,
                visibility=Visibility.GM_ONLY,
                effects={"action": "resolve", "thread_id": thread.id},
            )
            events.append(event)
            changes.append(
                StateDiffChange(
                    target="threads",
                    id=thread.id,
                    op="set",
                    path="status",
                    value="resolved",
                    visibility=Visibility.GM_ONLY,
                    source_event=event.id,
                )
            )

    return changes, rejected, events


def _changes_for_event(context: TurnContext, event: Event) -> list[StateDiffChange]:
    changes = []
    character_id = event.effects.get("character_id") or event.effects.get("target_id")
    scene_id = event.effects.get("scene_id") or event.effects.get("target_id")
    if event.type == "threat_pressure":
        threat_id = event.effects.get("threat_id")
        changes.append(
            StateDiffChange(
                target="world",
                op="set",
                path=f"threats.{threat_id}.pressure",
                value=event.effects.get("pressure"),
                visibility=Visibility.GM_ONLY,
                source_event=event.id,
            )
        )
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
    changes.extend(_scene_transition_changes(context, event))
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


def _find_scene(context: TurnContext, scene_id: str | None):
    if scene_id is None:
        return None
    return next((scene for scene in context.bundle.scenes if scene.id == scene_id), None)


def _scene_transition_changes(context: TurnContext, event: Event) -> list[StateDiffChange]:
    """Issue 009: ``effects.scene_transition: {"end": <id>, "start": <id>}`` ends one scene,
    activates the next (template-defined, pending), and carries active_characters over when
    the start scene doesn't already define its own cast.
    """
    transition = event.effects.get("scene_transition")
    if not isinstance(transition, dict):
        return []
    changes = []
    end_id = transition.get("end")
    start_id = transition.get("start")
    if end_id:
        changes.append(
            StateDiffChange(
                target="scene",
                id=end_id,
                op="set",
                path="status",
                value=SceneStatus.ENDED.value,
                visibility=Visibility.CANON,
                source_event=event.id,
            )
        )
    if start_id:
        changes.append(
            StateDiffChange(
                target="scene",
                id=start_id,
                op="set",
                path="status",
                value=SceneStatus.ACTIVE.value,
                visibility=Visibility.CANON,
                source_event=event.id,
            )
        )
        start_scene = _find_scene(context, start_id)
        end_scene = _find_scene(context, end_id)
        if (
            start_scene is not None
            and start_scene.status == SceneStatus.PENDING
            and not start_scene.active_characters
            and end_scene is not None
        ):
            changes.append(
                StateDiffChange(
                    target="scene",
                    id=start_id,
                    op="set",
                    path="active_characters",
                    value=list(end_scene.active_characters),
                    visibility=Visibility.CANON,
                    source_event=event.id,
                )
            )
    return changes


def _invalid_scene_transition_reason(context: TurnContext, change: StateDiffChange) -> str | None:
    """Custom rejection reasons for the start-side of a scene_transition (D009 guard)."""
    if not (change.target == "scene" and change.path == "status" and change.value == "active"):
        return None
    scene = _find_scene(context, change.id)
    if scene is None:
        return "scene_transition start target not found"
    if scene.status != SceneStatus.PENDING:
        return "scene_transition start target not pending"
    return None


def _reject(change: StateDiffChange, reason: str) -> RejectedChange:
    return RejectedChange(change=change, reason=reason)
