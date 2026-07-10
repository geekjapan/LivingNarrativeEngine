from living_narrative.intervention.permissions import PermissionRejection, check_permission
from living_narrative.intervention.schema import InterventionType
from living_narrative.session.mode import (
    is_gm_vault_visible,
    is_intervention_allowed,
    session_permission_table,
)


def test_watcher_mode_rejects_any_intervention_at_generation_hook():
    result = check_permission(
        InterventionType.SCENE_DIRECTIVE,
        "watcher",
        session_permission_table(),
    )

    assert isinstance(result, PermissionRejection)
    assert result.allowed_user_modes


def test_assistant_gm_rejects_canon_edit():
    result = check_permission(
        InterventionType.CANON_EDIT,
        "assistant_gm",
        session_permission_table(),
    )

    assert isinstance(result, PermissionRejection)
    assert "assistant_gm" not in result.allowed_user_modes


def test_gm_vault_visibility_follows_user_mode():
    assert is_gm_vault_visible("author") is False
    assert is_gm_vault_visible("full_gm") is True


def test_player_character_directive_must_target_bound_character():
    assert (
        is_intervention_allowed(
            "player_character",
            "character_directive",
            player_char_id="char_002",
            target_id="char_002",
        )
        is True
    )
    assert (
        is_intervention_allowed(
            "player_character",
            "character_directive",
            player_char_id="char_002",
            target_id="char_001",
        )
        is False
    )


def test_player_character_check_must_target_bound_character():
    assert is_intervention_allowed(
        "player_character",
        "dice_roll_request",
        player_char_id="char_002",
        target_id="char_002",
    )
    assert not is_intervention_allowed(
        "player_character",
        "dice_roll_request",
        player_char_id="char_002",
        target_id="char_001",
    )
