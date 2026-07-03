"""User-mode permission matrix owned by session-autonomy."""

from dataclasses import dataclass

from living_narrative.intervention.permissions import PermissionTable
from living_narrative.intervention.schema import InterventionType
from living_narrative.state.models import UserMode

ALL_INTERVENTIONS = frozenset(InterventionType)
ASSISTANT_GM_INTERVENTIONS = frozenset(
    {
        InterventionType.SCENE_DIRECTIVE,
        InterventionType.CHARACTER_DIRECTIVE,
        InterventionType.WORLD_DIRECTIVE,
        InterventionType.PACING_CONTROL,
        InterventionType.TONE_CONTROL,
        InterventionType.REVEAL_CONTROL,
        InterventionType.STOP_CONDITION,
    }
)
FULL_GM_INTERVENTIONS = ASSISTANT_GM_INTERVENTIONS | frozenset(
    {
        InterventionType.EVENT_INJECTION,
        InterventionType.PROBABILITY_BIAS,
        InterventionType.HIDDEN_TRUTH_EDIT,
        InterventionType.CANON_EDIT,
        InterventionType.DICE_ROLL_REQUEST,
        InterventionType.SCENE_PIVOT,
        InterventionType.RELATIONSHIP_EDIT,
        InterventionType.MEMORY_EDIT,
    }
)
AUTHOR_INTERVENTIONS = frozenset(
    {
        InterventionType.SCENE_DIRECTIVE,
        InterventionType.TONE_CONTROL,
        InterventionType.PACING_CONTROL,
        InterventionType.STOP_CONDITION,
    }
)
PLAYER_CHARACTER_INTERVENTIONS = frozenset(
    {InterventionType.CHARACTER_DIRECTIVE, InterventionType.STOP_CONDITION}
)


@dataclass(frozen=True)
class ModePermissions:
    allowed_interventions: frozenset[InterventionType]
    requires_diff_review: bool
    can_view_gm_vault: bool


MODE_PERMISSIONS: dict[UserMode, ModePermissions] = {
    UserMode.WATCHER: ModePermissions(frozenset(), False, False),
    UserMode.ASSISTANT_GM: ModePermissions(ASSISTANT_GM_INTERVENTIONS, True, True),
    UserMode.FULL_GM: ModePermissions(FULL_GM_INTERVENTIONS, True, True),
    UserMode.AUTHOR: ModePermissions(AUTHOR_INTERVENTIONS, True, False),
    UserMode.PLAYER_CHARACTER: ModePermissions(PLAYER_CHARACTER_INTERVENTIONS, True, False),
    UserMode.GOD: ModePermissions(ALL_INTERVENTIONS, False, True),
}


def is_intervention_allowed(
    user_mode: UserMode | str,
    intervention_type: InterventionType | str,
    *,
    player_char_id: str | None = None,
    target_id: str | None = None,
) -> bool:
    mode = UserMode(user_mode)
    type_ = InterventionType(intervention_type)
    if type_ not in MODE_PERMISSIONS[mode].allowed_interventions:
        return False
    if (
        mode == UserMode.PLAYER_CHARACTER
        and type_ == InterventionType.CHARACTER_DIRECTIVE
        and player_char_id is not None
    ):
        return target_id == player_char_id
    return True


def is_gm_vault_visible(user_mode: UserMode | str) -> bool:
    return MODE_PERMISSIONS[UserMode(user_mode)].can_view_gm_vault


def session_permission_table() -> PermissionTable:
    table: PermissionTable = {}
    for intervention_type in InterventionType:
        allowed = frozenset(
            mode
            for mode, permissions in MODE_PERMISSIONS.items()
            if intervention_type in permissions.allowed_interventions
        )
        table[intervention_type] = allowed
    return table
