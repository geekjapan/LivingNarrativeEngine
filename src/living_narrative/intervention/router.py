"""Type-based routing helpers (spec.md Requirement "Type別ルーティング").

``character_directive``/``world_directive``/``event_injection``/``canon_edit``/
``hidden_truth_edit``/``dice_roll_request`` are routed by shaping ``WorldEventCandidate``s
(world_simulator) or ``StateDiffChange``s (state_manager) directly — see those modules. This
module covers the routing that has no natural home in an existing agent: which interventions
reach a given Character Agent's context, and the tone_control -> Narrator wire.
"""

from typing import Any

from living_narrative.state.models import CharacterId, WorldStateBundle

# scene_directive broadcasts to the scene; the 5 unhandled types are presented to every active
# character as constraints (spec.md Requirement "Type別ハンドリング状況の明示"); character_directive
# is scoped to its target. stop_condition is deliberately excluded (delegated to session-autonomy).
_BROADCAST_TYPES = frozenset(
    {"probability_bias", "pacing_control", "scene_pivot", "relationship_edit", "memory_edit"}
)
_CHARACTER_CONTEXT_TYPES = _BROADCAST_TYPES | {"scene_directive", "character_directive"}


def character_directives_for(
    interventions: list[dict[str, Any]],
    character_id: CharacterId,
    bundle: WorldStateBundle,
) -> list[dict[str, Any]]:
    """Interventions this character's context may see, and no one else's (spec-foundation §4.3)."""
    character_scene_ids = {
        scene.id for scene in bundle.scenes if character_id in scene.active_characters
    }
    result = []
    for item in interventions:
        item_type = item.get("type")
        if item_type not in _CHARACTER_CONTEXT_TYPES:
            continue
        target_id = (item.get("target") or {}).get("id")
        if item_type == "character_directive":
            if target_id == character_id:
                result.append(item)
        elif item_type == "scene_directive":
            if target_id is None or target_id in character_scene_ids:
                result.append(item)
        else:
            result.append(item)
    return result


def resolve_tone_control(
    interventions: list[dict[str, Any]], override: str | None = None
) -> str | None:
    """The ``tone_control`` string to pass to the Narrator: an explicit override wins, else the
    latest ``tone_control`` intervention's ``content`` this turn, else ``None``.
    """
    if override is not None:
        return override
    for item in reversed(interventions):
        if item.get("type") == "tone_control":
            return item.get("content")
    return None
