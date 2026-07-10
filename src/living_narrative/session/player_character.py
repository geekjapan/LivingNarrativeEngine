"""player_character mode boundaries owned by session-autonomy (D114)."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from living_narrative.intervention.schema import (
    Intervention,
    InterventionTarget,
    InterventionType,
)
from living_narrative.session.mode import is_intervention_allowed
from living_narrative.state.models import (
    CharacterStatus,
    InventoryItem,
    ProjectConfig,
    SceneState,
    SceneStatus,
    UserMode,
    Visibility,
    WorldStateBundle,
)


class InventoryUseConstraints(BaseModel):
    """The only structured character-directive constraint PC mode accepts."""

    model_config = ConfigDict(extra="forbid")

    inventory_action: Literal["use"]
    item_id: str = Field(min_length=1, pattern=r"^item_\d+$")
    qty: int = Field(strict=True, gt=0)


class PlayerCharacterAuditRejection(BaseModel):
    type: InterventionType
    requested_user_mode: UserMode = UserMode.PLAYER_CHARACTER
    target: InterventionTarget
    reason: str


@dataclass
class PlayerCharacterPolicyResult:
    interventions: list[Intervention] = field(default_factory=list)
    rejections: list[PlayerCharacterAuditRejection] = field(default_factory=list)


def apply_player_character_intervention_policy(
    project: ProjectConfig,
    bundle: WorldStateBundle,
    interventions: list[Intervention],
) -> PlayerCharacterPolicyResult:
    """Enforce bound-PC targets and convert unavailable-PC input to an audited stop."""
    if project.user_mode is not UserMode.PLAYER_CHARACTER:
        return PlayerCharacterPolicyResult(interventions=list(interventions))

    player_char_id = project.player_char_id
    player = next((item for item in bundle.characters if item.id == player_char_id), None)
    result = PlayerCharacterPolicyResult()
    for item in interventions:
        reason = _pc_rejection_reason(item, player_char_id, player is not None)
        if reason is not None:
            result.rejections.append(_audit_rejection(item, reason))
            continue
        if (
            player is not None
            and player.status is not CharacterStatus.ALIVE
            and item.type
            in {InterventionType.CHARACTER_DIRECTIVE, InterventionType.DICE_ROLL_REQUEST}
        ):
            result.rejections.append(
                _audit_rejection(item, f"bound player character is {player.status.value}")
            )
            result.interventions.append(_stop_for_unavailable_player(item, player.status))
            continue
        if (
            player is not None
            and item.type
            in {InterventionType.CHARACTER_DIRECTIVE, InterventionType.DICE_ROLL_REQUEST}
            and not _is_active_scene_participant(bundle, player.id)
        ):
            result.rejections.append(
                _audit_rejection(item, "bound player character is not in the active scene")
            )
            continue
        result.interventions.append(item)
    return result


def _pc_rejection_reason(
    item: Intervention, player_char_id: str | None, player_exists: bool
) -> str | None:
    if item.type is InterventionType.STOP_CONDITION:
        if item.target.kind != "world" or item.target.id is not None:
            return "player_character stop_condition must target world without an id"
        return None
    if not player_exists:
        return "bound player character does not exist"
    if not is_intervention_allowed(
        UserMode.PLAYER_CHARACTER,
        item.type,
        player_char_id=player_char_id,
        target_id=item.target.id,
    ):
        return "player_character target must be the bound player_char_id"
    if item.target.kind != "character":
        return "player_character action/check target kind must be character"
    if item.type is InterventionType.DICE_ROLL_REQUEST:
        requested_character = item.constraints.get("character_id")
        if requested_character not in {None, player_char_id}:
            return "character check constraints.character_id must match the bound player_char_id"
        return None
    if item.type is InterventionType.CHARACTER_DIRECTIVE:
        if not item.constraints:
            return None
        try:
            InventoryUseConstraints.model_validate(item.constraints)
        except ValidationError as exc:
            return f"invalid inventory use constraints: {exc.errors()[0]['msg']}"
    return None


def _audit_rejection(item: Intervention, reason: str) -> PlayerCharacterAuditRejection:
    return PlayerCharacterAuditRejection(type=item.type, target=item.target, reason=reason)


def _stop_for_unavailable_player(item: Intervention, status: CharacterStatus) -> Intervention:
    data = item.model_dump(mode="json")
    data.update(
        {
            "type": InterventionType.STOP_CONDITION.value,
            "target": {"kind": "world"},
            "content": (
                f"PC {item.target.id} は {status.value} のため、入力を適用せずレビューへ送る: "
                f"{item.content}"
            ),
            "constraints": {},
        }
    )
    return Intervention.model_validate(data)


def _is_active_scene_participant(bundle: WorldStateBundle, player_char_id: str) -> bool:
    active_scene = next(
        (scene for scene in bundle.scenes if scene.status is SceneStatus.ACTIVE), None
    )
    return active_scene is not None and player_char_id in active_scene.active_characters


class PlayerCharacterKnowledgeView(BaseModel):
    knows: list[str]
    believes: list[str]


class PlayerCharacterView(BaseModel):
    id: str
    name: str
    status: CharacterStatus
    stats: dict[str, int]
    skills: dict[str, int]
    knowledge: PlayerCharacterKnowledgeView
    secrets: list[str]
    private_mind: list[str]
    inventory: list[InventoryItem]


class PlayerCharacterProjection(BaseModel):
    world_parameters: dict[str, int] = Field(default_factory=dict)
    visible_facts: list[str] = Field(default_factory=list)
    characters: list[PlayerCharacterView]
    scene: "PlayerCharacterSceneView | None" = None


class PlayerCharacterSceneView(BaseModel):
    id: str
    location: str
    mood: str


def build_player_character_projection(
    project: ProjectConfig,
    bundle: WorldStateBundle,
    active_scene: SceneState | None,
) -> PlayerCharacterProjection:
    """Build the single validated CLI/web projection for a bound player character."""
    if project.user_mode is not UserMode.PLAYER_CHARACTER or project.player_char_id is None:
        raise ValueError("player character projection requires a bound player_character project")
    player = next((item for item in bundle.characters if item.id == project.player_char_id), None)
    if player is None:
        raise ValueError("bound player character does not exist")

    player_in_scene = active_scene is not None and player.id in active_scene.active_characters
    visible_facts: list[str] = []
    scene_view = None
    if active_scene is not None and player_in_scene:
        scene_view = PlayerCharacterSceneView(
            id=active_scene.id,
            location=active_scene.location,
            mood=active_scene.mood,
        )
        visible_facts.extend(active_scene.reader_visible_facts)
        visible_facts.extend(
            fact.text
            for fact in active_scene.hidden_facts
            if fact.visibility is Visibility.READER
            or player.id in fact.known_by
            or fact.visibility is Visibility.SCENE
        )
    return PlayerCharacterProjection(
        characters=[
            PlayerCharacterView(
                id=player.id,
                name=player.name,
                status=player.status,
                stats=player.stats,
                skills=player.skills,
                knowledge=PlayerCharacterKnowledgeView(
                    knows=player.knowledge.knows,
                    believes=player.knowledge.believes,
                ),
                secrets=player.secrets,
                private_mind=player.private_mind,
                inventory=player.inventory,
            )
        ],
        visible_facts=visible_facts,
        scene=scene_view,
    )
