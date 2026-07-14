"""Shared deterministic checks for authored scene affordances."""

from typing import Any

from living_narrative.state.models import Visibility, WorldStateBundle


def affordance_visible_to_character(affordance: Any, character_id: str | None) -> bool:
    if affordance.visibility in {Visibility.READER, Visibility.SCENE, Visibility.CANON}:
        return True
    return affordance.visibility == Visibility.CHARACTER and character_id in affordance.known_by


def affordance_prerequisites_met(
    bundle: WorldStateBundle,
    prerequisites: Any,
) -> bool:
    facts = (
        {item.id for item in bundle.reader_state}
        | {item.id for item in bundle.canon}
        | {fact.id for scene in bundle.scenes for fact in scene.hidden_facts}
    )
    if any(item not in facts for item in prerequisites.required_fact_ids):
        return False
    quests = {item.id: item.status for item in bundle.quests}
    if any(quests.get(item) != status for item, status in prerequisites.quest_statuses.items()):
        return False
    threads = {item.id: item.status for item in bundle.unresolved_threads}
    return all(
        threads.get(item) == status for item, status in prerequisites.thread_statuses.items()
    )
