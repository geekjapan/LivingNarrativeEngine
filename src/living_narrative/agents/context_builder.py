"""Scope-safe context construction."""

from typing import Any

from pydantic import BaseModel

from living_narrative.agents.models import CharacterAgentInput, EligibleCombatTarget
from living_narrative.state.models import (
    CharacterId,
    Event,
    OpenQuestInfo,
    SceneStatus,
    Visibility,
    WorldStateBundle,
    latest_memory_summary,
)

DEFAULT_EVENT_LIMIT = 20


class WorldContext(BaseModel):
    bundle: WorldStateBundle
    requires_visibility: bool = True


def build_character_context(
    bundle: WorldStateBundle,
    character_id: CharacterId,
    *,
    events: list[Event] | None = None,
    directives: list[dict[str, Any]] | None = None,
    event_limit: int = DEFAULT_EVENT_LIMIT,
) -> CharacterAgentInput:
    character = _find_character(bundle, character_id)
    scene_facts = []
    eligible_combat_targets: list[EligibleCombatTarget] = []
    for scene in bundle.scenes:
        if scene.status != SceneStatus.ACTIVE:
            continue
        if character_id not in scene.active_characters:
            continue
        active_ids = set(scene.active_characters)
        eligible_combat_targets = [
            EligibleCombatTarget(id=item.id)
            for item in bundle.characters
            if item.id != character_id and item.id in active_ids and "hp" in item.stats
        ]
        scene_facts.extend(scene.reader_visible_facts)
        if scene.summary:
            scene_facts.append(scene.summary)
        scene_facts.extend(
            fact.text
            for fact in scene.hidden_facts
            if fact.visibility == Visibility.READER or character_id in fact.known_by
        )

    scoped_events = [
        event for event in events or [] if _event_visible_to_character(event, character_id)
    ][-event_limit:]
    relationships = [
        relationship
        for relationship in bundle.relationships
        if relationship.from_ == character_id or relationship.to == character_id
    ]
    character_directives = [
        directive
        for directive in directives or []
        if directive.get("character_id") in (None, character_id)
        or directive.get("target_id") == character_id
    ]
    # 015: the latest memory summary is reader-visible by construction (narrator-authored from
    # reader-visible material only), so handing it to the character is leak-safe.
    memory_summary = latest_memory_summary(bundle.memory_summaries)
    return CharacterAgentInput(
        character_id=character_id,
        scoped_state=character.model_copy(deep=True),
        visible_events=scoped_events,
        visible_facts=[
            *character.knowledge.knows,
            *scene_facts,
            *([memory_summary] if memory_summary else []),
        ],
        relationships=relationships,
        directives=character_directives,
        open_quests=[
            OpenQuestInfo(
                id=quest.id,
                title=quest.title,
                status=quest.status,
                objectives=list(quest.objectives),
            )
            for quest in bundle.quests
            if quest.status in {"open", "advanced"}
        ],
        eligible_combat_targets=eligible_combat_targets,
    )


def build_world_context(bundle: WorldStateBundle) -> WorldContext:
    return WorldContext(bundle=bundle.model_copy(deep=True))


def _find_character(bundle: WorldStateBundle, character_id: CharacterId):
    for character in bundle.characters:
        if character.id == character_id:
            return character
    raise ValueError(f"character not found: {character_id}")


def _event_visible_to_character(event: Event, character_id: CharacterId) -> bool:
    if character_id in event.hidden_from:
        return False
    if event.visibility in {Visibility.READER, Visibility.SCENE, Visibility.CANON}:
        return True
    if event.visibility == Visibility.CHARACTER:
        return character_id in event.known_by
    return False
