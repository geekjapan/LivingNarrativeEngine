"""State Manager BuildDiff slot implementation."""

import re
from collections.abc import Callable
from typing import Any

from living_narrative.agents.affordance_policy import (
    affordance_prerequisites_met,
    affordance_visible_to_character,
)
from living_narrative.agents.models import CharacterAgentOutput, CharacterQuestUpdateCandidate
from living_narrative.intervention.reveal import must_not_reveal_texts, reveal_now_sources
from living_narrative.narration.models import NarratorQuestUpdateCandidate, ThreadUpdateCandidate
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import BuildDiffOutput, RejectedChange
from living_narrative.state.diff import StateDiff, StateDiffChange, StateDiffError, apply_state_diff
from living_narrative.state.models import (
    CanonEntry,
    CharacterId,
    CharacterStatus,
    Event,
    InventoryItem,
    Quest,
    ReaderStateEntry,
    SceneStatus,
    TimelineEntry,
    UnresolvedThread,
    Visibility,
)

_ROOT_ENTRY_MODELS: dict[str, type] = {
    "threads": UnresolvedThread,
    "quests": Quest,
    "canon": CanonEntry,
    "reader_state": ReaderStateEntry,
}

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
    narrator_quest_updates: list[NarratorQuestUpdateCandidate] | None = None,
    memory_summary_update: str | None = None,
) -> BuildDiffOutput:
    allocate_event_id = allocate_event_id or _default_event_id_allocator()
    must_not_reveal = must_not_reveal_texts(context, interventions)
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    synthetic_events: list[Event] = []

    # Turn-wide projections (shared across every action_outcome event this turn) so a thread
    # or quest accepted/advanced by an earlier outcome is visible to a later one in the same
    # turn, instead of each event validating only against the turn's starting bundle.
    accepted_thread_ids: set[str] = set()
    projected_thread_statuses = {item.id: item.status for item in context.bundle.unresolved_threads}
    projected_quest_statuses = {item.id: item.status for item in context.bundle.quests}
    accepted_root_ids: dict[str, set[str]] = {
        "canon": set(),
        "reader_state": set(),
        "quests": set(),
    }

    for event in resolved_events:
        if event.type == "action_outcome":
            outcome_changes, outcome_rejected, outcome_events = _action_outcome_changes(
                context,
                event,
                allocate_event_id,
                accepted_thread_ids=accepted_thread_ids,
                projected_thread_statuses=projected_thread_statuses,
                projected_quest_statuses=projected_quest_statuses,
                accepted_root_ids=accepted_root_ids,
                must_not_reveal=must_not_reveal,
            )
            changes.extend(outcome_changes)
            rejected.extend(outcome_rejected)
            synthetic_events.extend(outcome_events)
            candidates = []
        else:
            candidates = _changes_for_event(context, event)
        for candidate in candidates:
            transition_reason = _invalid_scene_transition_reason(context, candidate)
            faction_reason = _invalid_faction_move_reason(context, candidate)
            if candidate.source_event is None:
                rejected.append(_reject(candidate, "missing source_event"))
            elif _blocked_reveal(candidate, must_not_reveal):
                rejected.append(_reject(candidate, "blocked by reveal_control must-not-reveal"))
            elif transition_reason is not None:
                rejected.append(_reject(candidate, transition_reason))
            elif faction_reason is not None:
                rejected.append(_reject(candidate, faction_reason))
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

    character_quest_updates = [
        update for _, output in character_outputs or [] for update in output.quest_updates
    ]
    quest_changes, quest_rejected = _quest_update_changes(
        context,
        character_quest_updates,
        narrator_quest_updates or [],
        resolved_events,
    )
    changes.extend(quest_changes)
    rejected.extend(quest_rejected)

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
    authored_thread_events = [
        event
        for event in synthetic_events
        if event.type == "thread_update" and event.cause and event.cause.startswith("authored:")
    ]
    thread_changes, thread_rejected, thread_events = _thread_update_changes(
        context,
        thread_updates or [],
        resolved_events,
        allocate_event_id,
        authored_thread_events=authored_thread_events,
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
    inventory_changes, inventory_rejected = _inventory_update_changes(
        character_id, character, output
    )
    changes.extend(inventory_changes)
    rejected.extend(inventory_rejected)
    return changes, rejected


def _inventory_update_changes(
    character_id: CharacterId, character: Any, output: CharacterAgentOutput
) -> tuple[list[StateDiffChange], list[RejectedChange]]:
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    inventory = character.inventory if character is not None else []
    known_items = {item.id: item for item in inventory}
    remaining_qty = {item.id: item.qty for item in inventory}
    item_numbers = [
        int(item.id.removeprefix("item_"))
        for item in inventory
        if item.id.removeprefix("item_").isdigit()
    ]
    next_item_number = max(item_numbers, default=0) + 1

    for update in output.inventory_updates:
        stub = StateDiffChange(
            target="character",
            id=character_id,
            op="add",
            path="inventory",
            value=update.model_dump(mode="json"),
            visibility=Visibility.CHARACTER,
        )
        if update.qty <= 0:
            rejected.append(_reject(stub, "inventory update qty must be positive"))
            continue
        if update.action == "gain":
            if not update.name or not update.name.strip():
                rejected.append(_reject(stub, "inventory gain requires name"))
                continue
            item = InventoryItem(
                id=f"item_{next_item_number:03d}",
                name=update.name,
                qty=update.qty,
                note=update.note,
            )
            next_item_number += 1
            changes.append(
                StateDiffChange(
                    target="character",
                    id=character_id,
                    op="add",
                    path="inventory",
                    value=item,
                    visibility=Visibility.CHARACTER,
                )
            )
            continue

        item = known_items.get(update.item_id or "")
        if item is None:
            rejected.append(_reject(stub, f"unknown inventory item: {update.item_id!r}"))
            continue
        available = remaining_qty[item.id]
        if update.qty > available:
            rejected.append(
                _reject(stub, f"inventory update exceeds stock for {item.id}: {available}")
            )
            continue
        remaining_qty[item.id] -= update.qty
        if remaining_qty[item.id] == 0:
            changes.append(
                StateDiffChange(
                    target="character",
                    id=character_id,
                    op="remove",
                    path="inventory",
                    value={"id": item.id},
                    visibility=Visibility.CHARACTER,
                )
            )
        else:
            changes.append(
                StateDiffChange(
                    target="character",
                    id=character_id,
                    op="set",
                    path=f"inventory.{item.id}.qty",
                    value=remaining_qty[item.id],
                    visibility=Visibility.CHARACTER,
                )
            )
    return changes, rejected


def _quest_update_changes(
    context: TurnContext,
    character_updates: list[CharacterQuestUpdateCandidate],
    narrator_updates: list[NarratorQuestUpdateCandidate],
    resolved_events: list[Event],
) -> tuple[list[StateDiffChange], list[RejectedChange]]:
    """Convert explicit quest proposals to validated, reader-visible diffs."""
    projected_status = {quest.id: quest.status for quest in context.bundle.quests}
    projected_related = {quest.id: set(quest.related_event_ids) for quest in context.bundle.quests}
    related_event_ids = [
        event.id for event in resolved_events if event.visibility == Visibility.READER
    ]
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []

    sourced_updates = [
        *(("character", update) for update in character_updates),
        *(("narrator", update) for update in narrator_updates),
    ]
    for source, update in sourced_updates:
        stub = StateDiffChange(
            target="quests",
            id=update.quest_id,
            op="add" if update.action == "open" else "set",
            path="" if update.action == "open" else "status",
            value=update.model_dump(mode="json"),
            visibility=Visibility.READER,
        )
        if not re.fullmatch(r"quest_\d{3,}", update.quest_id):
            rejected.append(_reject(stub, f"invalid quest_id: {update.quest_id!r}"))
            continue

        if source == "character" and update.action == "open":
            rejected.append(_reject(stub, "character cannot open reader-visible quest"))
            continue

        if update.action == "open":
            if update.quest_id in projected_status:
                rejected.append(_reject(stub, f"duplicate quest_id: {update.quest_id}"))
                continue
            if not update.title or not update.title.strip():
                rejected.append(_reject(stub, "open quest update missing title"))
                continue
            changes.append(
                StateDiffChange(
                    target="quests",
                    op="add",
                    path="",
                    value={
                        "id": update.quest_id,
                        "title": update.title,
                        "status": "open",
                        "objectives": update.objectives,
                        "related_event_ids": related_event_ids,
                    },
                    visibility=Visibility.READER,
                )
            )
            projected_status[update.quest_id] = "open"
            projected_related[update.quest_id] = set(related_event_ids)
            continue

        status = projected_status.get(update.quest_id)
        if status is None:
            rejected.append(_reject(stub, f"unknown quest_id: {update.quest_id!r}"))
            continue
        if status in {"resolved", "failed"}:
            rejected.append(
                _reject(stub, f"quest cannot transition from {status}: {update.quest_id}")
            )
            continue

        next_status = "advanced" if update.action == "advance" else "resolved"
        changes.append(
            StateDiffChange(
                target="quests",
                id=update.quest_id,
                op="set",
                path="status",
                value=next_status,
                visibility=Visibility.READER,
            )
        )
        for event_id in related_event_ids:
            if event_id not in projected_related[update.quest_id]:
                changes.append(
                    StateDiffChange(
                        target="quests",
                        id=update.quest_id,
                        op="add",
                        path="related_event_ids",
                        value=event_id,
                        visibility=Visibility.READER,
                    )
                )
                projected_related[update.quest_id].add(event_id)
        projected_status[update.quest_id] = next_status

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
    authored_thread_events: list[Event] | None = None,
) -> tuple[list[StateDiffChange], list[RejectedChange], list[Event]]:
    """Issue 014: convert narrator ``thread_updates`` into ``threads``-target diff changes.

    Each accepted update also emits a synthetic ``gm_only`` ``thread_update`` event (mirroring
    ``_synthetic_edit_change``) so ``pacing.detect_stall`` can see advance/resolve as narrative
    progress (open does not count — see ``agents/pacing.py``). Rejected updates never produce
    an event: unknown ``thread_id``, an ``advance``/``resolve`` on an already-resolved thread,
    and an ``open`` missing ``description`` are all declined without side effects.
    """
    known_threads = {thread.id: thread for thread in context.bundle.unresolved_threads}
    authored_thread_events = authored_thread_events or []
    authored_thread_ids = {
        event.effects.get("thread_id")
        for event in authored_thread_events
        if event.effects.get("thread_id")
    }
    this_turn_event_ids = [event.id for event in resolved_events]
    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    events: list[Event] = []
    open_index = 0

    for update in thread_updates:
        if update.action == "open":
            if authored_thread_ids:
                stub = StateDiffChange(
                    target="threads", op="add", path="", value={}, visibility=Visibility.GM_ONLY
                )
                rejected.append(
                    _reject(stub, "narrator thread open conflicts with authored thread")
                )
                continue
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
        if update.thread_id in authored_thread_ids:
            # Authored thread declarations are applied before narrator proposals. The
            # synthetic event carries the safe description/status transition, so a narrator
            # proposal cannot reopen or contradict it in this turn.
            stub = StateDiffChange(
                target="threads",
                id=update.thread_id,
                op="set" if update.action == "resolve" else "add",
                path="status" if update.action == "resolve" else "notes",
                value="resolved" if update.action == "resolve" else update.note,
                visibility=Visibility.GM_ONLY,
            )
            rejected.append(_reject(stub, "narrator thread update conflicts with authored thread"))
            continue
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


def _action_outcome_changes(
    context: TurnContext,
    event: Event,
    allocate_event_id: Callable[[], str],
    accepted_thread_ids: set[str],
    projected_thread_statuses: dict[str, str],
    projected_quest_statuses: dict[str, str],
    accepted_root_ids: dict[str, set[str]],
    must_not_reveal: set[Any],
) -> tuple[list[StateDiffChange], list[RejectedChange], list[Event]]:
    """Re-validate authored outcome declarations and turn them into StateDiff changes."""
    payload = event.effects.get("action_outcome")
    if not isinstance(payload, dict) or not event.effects.get("accepted"):
        return [], [], []
    affordance_id = payload.get("affordance_id")
    affordance = next(
        (
            affordance
            for scene in context.bundle.scenes
            for affordance in getattr(scene, "affordances", [])
            if affordance.id == affordance_id
        ),
        None,
    )
    if affordance is None:
        return [], [_outcome_rejection(event, "unknown_affordance")], []
    character_id = payload.get("character_id")
    active_scene = next(
        (
            scene
            for scene in context.bundle.scenes
            if scene.status == "active"
            and affordance in getattr(scene, "affordances", [])
            and character_id in scene.active_characters
        ),
        None,
    )
    if active_scene is None:
        return [], [_outcome_rejection(event, "affordance_not_active")], []
    is_fallback = (
        isinstance(payload.get("consumption"), dict)
        and payload["consumption"].get("fallback") is True
    )
    # A fallback is engine-forced, not a character choice from a prompt list, so
    # prompt-visibility (e.g. a gm_only fallback affordance) must not block it.
    if not is_fallback and not affordance_visible_to_character(affordance, character_id):
        return [], [_outcome_rejection(event, "not_visible")], []
    if not affordance_prerequisites_met(
        context.bundle,
        affordance.prerequisites,
        quest_status_overrides=projected_quest_statuses,
        thread_status_overrides=projected_thread_statuses,
    ):
        return [], [_outcome_rejection(event, "prerequisites_unmet")], []
    if payload.get("character_id") not in (affordance.actor_ids or [payload.get("character_id")]):
        return [], [_outcome_rejection(event, "actor_not_allowed")], []
    if affordance.recurrence == "once" and affordance.used_event_ids:
        return [], [_outcome_rejection(event, "already_used")], []
    if getattr(affordance, "fallback_only", False) and not is_fallback:
        return [], [_outcome_rejection(event, "fallback_only")], []
    declarations = payload.get("outcomes")
    if not isinstance(declarations, list):
        return [], [_outcome_rejection(event, "invalid_outcome")], []
    authored_declarations = [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        for item in affordance.outcomes
    ]
    if declarations != authored_declarations:
        return [], [_outcome_rejection(event, "invalid_outcome")], []

    changes: list[StateDiffChange] = []
    rejected: list[RejectedChange] = []
    thread_events: list[Event] = []
    for raw in declarations:
        try:
            from living_narrative.state.models import AffordanceOutcome

            outcome = AffordanceOutcome.model_validate(raw)
            declaration = outcome.model_dump(mode="json")
            value = _runtime_outcome_value(outcome.target, declaration["value"], context, event)
            change = StateDiffChange(
                target=outcome.target,
                op=outcome.op,
                path=outcome.path,
                id=outcome.id,
                value=value,
                visibility=outcome.visibility,
                source_event=event.id,
            )
        except Exception:
            rejected.append(_outcome_rejection(event, "invalid_outcome"))
            continue
        if change.target == "scene" and change.id is None:
            change = change.model_copy(update={"id": _active_scene_id(context)})
        if _blocked_reveal(change, must_not_reveal):
            rejected.append(_reject(change, "blocked by reveal_control must-not-reveal"))
            continue
        transition_reason = _invalid_scene_transition_reason(context, change)
        if transition_reason is not None:
            rejected.append(_reject(change, transition_reason))
            continue
        reason = _authored_outcome_rejection_reason(context, change)
        if change.target == "threads" and change.path == "status":
            current_status = projected_thread_statuses.get(change.id or "")
            if current_status is None:
                reason = "unknown_thread_id"
            elif current_status == "resolved":
                reason = "resolved_thread_is_terminal"
            elif change.value == current_status:
                reason = "no_op"
            elif change.value not in {"advanced", "resolved"}:
                reason = f"invalid_thread_transition:{current_status}->{change.value}"
            else:
                reason = None
        elif change.target == "quests" and change.path == "status":
            current_status = projected_quest_statuses.get(change.id or "")
            if current_status is None:
                reason = "unknown_quest_id"
            elif current_status in {"resolved", "failed"}:
                reason = "quest_already_terminal"
            elif change.value == current_status:
                reason = "no_op"
            elif change.value not in {"advanced", "resolved"}:
                reason = f"invalid_quest_transition:{current_status}->{change.value}"
            else:
                reason = None
        elif (
            reason is None
            and change.target in {"canon", "reader_state", "quests"}
            and change.path == ""
            and change.op == "add"
            and isinstance(change.value, dict)
            and change.value.get("id") in accepted_root_ids[change.target]
        ):
            reason = "duplicate_target"
        if reason is not None:
            rejected.append(_reject(change, reason))
            continue
        if change.target == "threads" and change.path == "" and change.op == "add":
            value = change.value if isinstance(change.value, dict) else {}
            thread_id = value.get("id")
            if change.visibility not in {Visibility.READER, Visibility.CANON}:
                rejected.append(_reject(change, "reader_invisible_thread"))
                continue
            if not thread_id or not value.get("description") or value.get("status") != "open":
                rejected.append(_reject(change, "invalid_authored_thread"))
                continue
            if (
                thread_id in {item.id for item in context.bundle.unresolved_threads}
                or thread_id in accepted_thread_ids
            ):
                rejected.append(_reject(change, "duplicate_authored_thread"))
                continue
            accepted_thread_ids.add(thread_id)
            projected_thread_statuses[thread_id] = "open"
            thread_events.append(
                Event(
                    id=allocate_event_id(),
                    turn=context.turn,
                    type="thread_update",
                    cause=f"authored:{affordance.id}",
                    text=value["description"],
                    visibility=Visibility.READER,
                    effects={"action": "open", "thread_id": thread_id, "authored": True},
                )
            )
        elif change.target == "threads" and change.path == "status":
            thread = next(
                (item for item in context.bundle.unresolved_threads if item.id == change.id), None
            )
            if thread is None:
                rejected.append(_reject(change, "unknown_thread_id"))
                continue
            action = "resolve" if change.value == "resolved" else "advance"
            if change.visibility not in {Visibility.READER, Visibility.CANON}:
                rejected.append(_reject(change, "reader_invisible_thread"))
                continue
            thread_events.append(
                Event(
                    id=allocate_event_id(),
                    turn=context.turn,
                    type="thread_update",
                    cause=f"authored:{affordance.id}",
                    text=thread.description,
                    visibility=Visibility.READER,
                    effects={"action": action, "thread_id": thread.id, "authored": True},
                )
            )
            projected_thread_statuses[thread.id] = change.value
        elif change.target == "quests" and change.path == "status":
            projected_quest_statuses[change.id or ""] = change.value
        elif (
            change.target in {"canon", "reader_state", "quests"}
            and change.path == ""
            and change.op == "add"
            and isinstance(change.value, dict)
            and change.value.get("id")
        ):
            accepted_root_ids[change.target].add(change.value["id"])
        changes.append(change)

    if affordance.recurrence == "once" and changes:
        scene = next(
            (
                scene
                for scene in context.bundle.scenes
                if any(item.id == affordance.id for item in scene.affordances)
            ),
            None,
        )
        if scene is not None:
            changes.append(
                StateDiffChange(
                    target="scene",
                    id=scene.id,
                    op="add",
                    path=f"affordances.{affordance.id}.used_event_ids",
                    value=event.id,
                    visibility=Visibility.GM_ONLY,
                    source_event=event.id,
                )
            )
    return changes, rejected, thread_events


def _outcome_rejection(event: Event, reason: str) -> RejectedChange:
    stub = StateDiffChange(
        target="scene",
        id=_event_scene_id(event),
        op="set",
        path="summary",
        value="",
        visibility=Visibility.GM_ONLY,
        source_event=event.id,
    )
    return _reject(stub, reason)


def _runtime_outcome_value(target: str, value: Any, context: TurnContext, event: Event) -> Any:
    """Authored YAML cannot forge provenance or stale turn markers."""
    if not isinstance(value, dict):
        return value
    value = dict(value)
    if target in {"canon", "reader_state"}:
        value["established_turn"] = context.turn
        value["source_event"] = event.id
        if target == "reader_state":
            value["disclosed_turn"] = context.turn
    elif target == "threads":
        value["opened_turn"] = context.turn
    return value


def _event_scene_id(event: Event) -> str:
    return event.effects.get("scene_id") or event.effects.get("target_id") or "scene_000"


def _authored_outcome_rejection_reason(context: TurnContext, change: StateDiffChange) -> str | None:
    if not _valid_target(context, change):
        return "target_not_found"
    if change.target in {"threads", "quests", "canon", "reader_state"} and change.path == "":
        collection = {
            "threads": context.bundle.unresolved_threads,
            "quests": context.bundle.quests,
            "canon": context.bundle.canon,
            "reader_state": context.bundle.reader_state,
        }[change.target]
        if change.op == "add":
            if not isinstance(change.value, dict):
                return "invalid_root_add_payload"
            if any(getattr(item, "id", None) == change.value.get("id") for item in collection):
                return "duplicate_target"
            if change.target in {"threads", "quests"} and change.value.get("status") != "open":
                return "invalid_root_add_payload"
            try:
                _ROOT_ENTRY_MODELS[change.target].model_validate(change.value)
            except Exception:
                return "invalid_root_add_payload"
        elif change.op == "remove":
            if not _remove_target_present(collection, change):
                return "invalid_remove_target"
        else:
            return "invalid_root_op"
        return _authored_dry_run_rejection(context, change)
    current = _authored_current_value(context, change)
    if current is None and change.op in {"set", "delta", "remove"}:
        return "target_not_found"
    if change.op == "set" and current == change.value:
        return "no_op"
    if change.op == "delta":
        if not isinstance(current, int):
            return "invalid_delta"
        if max(0, min(100, current + change.value)) == current:
            return "no_op"
    if change.op == "add":
        if not isinstance(current, list):
            return "invalid_add_target"
        if change.value in current:
            return "no_op"
    if change.op == "remove":
        if not isinstance(current, list):
            return "invalid_remove_target"
        if not _remove_target_present(current, change):
            return "invalid_remove_target"
    return _authored_dry_run_rejection(context, change)


def _authored_dry_run_rejection(context: TurnContext, change: StateDiffChange) -> str | None:
    """Catch-all: dry-run ``apply_state_diff`` (on a deep-copied bundle, no side effects) so
    an authored change that would raise at commit time -- an invalid enum value, a
    malformed list element, anything the structural checks above don't specifically name --
    is rejected here instead of aborting the whole turn or persisting invalid state."""
    trial = StateDiff(id="diff_000", turn=context.turn, changes=[change])
    try:
        apply_state_diff(context.bundle, trial)
    except StateDiffError:
        return "invalid_authored_change"
    return None


def _remove_target_present(current: list, change: StateDiffChange) -> bool:
    """Mirror ``state.diff._remove_value``'s matching rules (read-only) so an authored
    remove that would raise "remove target not found" at apply time is rejected here
    instead of failing the whole turn."""
    value = change.value
    if value is None and change.id is not None:
        return any(getattr(item, "id", None) == change.id for item in current)
    if isinstance(value, dict) and "id" in value:
        return any(getattr(item, "id", None) == value["id"] for item in current)
    if isinstance(value, dict):
        return any(
            hasattr(item, "model_dump") and item.model_dump(mode="json") == value
            for item in current
        )
    return value in current


def _authored_current_value(context: TurnContext, change: StateDiffChange) -> Any:
    target: Any
    if change.target == "world":
        target = context.bundle.world
    elif change.target == "character":
        target = next((item for item in context.bundle.characters if item.id == change.id), None)
    elif change.target == "scene":
        target = next((item for item in context.bundle.scenes if item.id == change.id), None)
    elif change.target == "threads":
        target = next(
            (item for item in context.bundle.unresolved_threads if item.id == change.id), None
        )
    elif change.target == "quests":
        target = next((item for item in context.bundle.quests if item.id == change.id), None)
    elif change.target == "canon":
        target = next((item for item in context.bundle.canon if item.id == change.id), None)
    elif change.target == "reader_state":
        target = next((item for item in context.bundle.reader_state if item.id == change.id), None)
    else:
        target = None
    if target is None or not change.path:
        return target
    current = target
    for part in change.path.split("."):
        if isinstance(current, list):
            current = next((item for item in current if getattr(item, "id", None) == part), None)
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _changes_for_event(context: TurnContext, event: Event) -> list[StateDiffChange]:
    # Structured action outcomes are the only action-driven mutation path. Arbitrary
    # character effects are stripped by Resolve and intentionally ignored here as well.
    if event.type in {"character_action", "character_dialogue", "character_inner_reaction"}:
        return []
    changes = []
    character_id = event.effects.get("character_id") or event.effects.get("target_id")
    scene_id = event.effects.get("scene_id") or event.effects.get("target_id")
    combat = event.effects.get("combat")
    if event.type == "combat" and isinstance(combat, dict):
        damage = combat.get("damage")
        if combat.get("result") == "success" and isinstance(damage, int) and damage > 0:
            changes.append(
                StateDiffChange(
                    target="character",
                    id=combat.get("defender"),
                    op="delta",
                    path="stats.hp",
                    value=-damage,
                    visibility=event.visibility,
                    source_event=event.id,
                )
            )
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
    if event.type == "faction_move":
        faction_id = event.effects.get("faction_id")
        for key, delta in sorted((event.effects.get("resource_deltas") or {}).items()):
            changes.append(
                StateDiffChange(
                    target="faction",
                    id=faction_id,
                    op="delta",
                    path=f"resources.{key}",
                    value=delta,
                    visibility=Visibility.GM_ONLY,
                    source_event=event.id,
                )
            )
        for key, delta in sorted((event.effects.get("relation_deltas") or {}).items()):
            changes.append(
                StateDiffChange(
                    target="faction",
                    id=faction_id,
                    op="delta",
                    path=f"relations.{key}",
                    value=delta,
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
    if isinstance(change.value, dict):
        value = change.value
        return bool({value.get("id"), value.get("fact_id"), value.get("text")} & must_not_reveal)
    # A scalar edit (e.g. op=set path=text on an existing entry) carries no dict to
    # inspect -- check the new text/id directly so a reveal_control block can't be
    # bypassed by rewriting an entry's text instead of adding a new one.
    return change.value in must_not_reveal or change.id in must_not_reveal


def _valid_target(context: TurnContext, change: StateDiffChange) -> bool:
    if change.target == "character":
        return any(character.id == change.id for character in context.bundle.characters)
    if change.target == "scene":
        return any(scene.id == change.id for scene in context.bundle.scenes)
    if change.target == "faction":
        return any(faction.id == change.id for faction in context.bundle.factions)
    if change.target == "threads":
        return change.id is None or any(
            item.id == change.id for item in context.bundle.unresolved_threads
        )
    if change.target == "quests":
        return change.id is None or any(item.id == change.id for item in context.bundle.quests)
    if change.target == "canon":
        return change.id is None or any(item.id == change.id for item in context.bundle.canon)
    if change.target == "reader_state":
        return change.id is None or any(
            item.id == change.id for item in context.bundle.reader_state
        )
    return True


def _invalid_faction_move_reason(context: TurnContext, change: StateDiffChange) -> str | None:
    if change.target != "faction":
        return None
    faction = next((item for item in context.bundle.factions if item.id == change.id), None)
    if faction is None:
        return f"unknown faction_id: {change.id!r}"
    scope, _, key = change.path.partition(".")
    if scope == "resources" and key not in faction.resources:
        return f"unknown faction resource key: {key!r}"
    if scope == "relations" and key not in faction.relations:
        return f"unknown faction relation key: {key!r}"
    return None


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
