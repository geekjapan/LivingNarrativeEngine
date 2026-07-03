from living_narrative.intervention.permissions import (
    PermissionOk,
    PermissionRejection,
    check_permission,
)
from living_narrative.intervention.schema import InterventionType


def test_canon_edit_is_rejected_for_watcher():
    result = check_permission(InterventionType.CANON_EDIT, "watcher")
    assert isinstance(result, PermissionRejection)
    assert result.allowed_user_modes == ["full_gm", "god"]


def test_canon_edit_is_allowed_for_god():
    result = check_permission(InterventionType.CANON_EDIT, "god")
    assert isinstance(result, PermissionOk)


def test_hidden_truth_edit_invariant_cannot_be_overridden_by_a_permissive_table():
    permission_table = {InterventionType.HIDDEN_TRUTH_EDIT: frozenset({"watcher"})}
    result = check_permission(InterventionType.HIDDEN_TRUTH_EDIT, "watcher", permission_table)
    assert isinstance(result, PermissionRejection)


def test_default_permission_table_is_permissive_for_non_invariant_types():
    result = check_permission(InterventionType.SCENE_DIRECTIVE, "watcher")
    assert isinstance(result, PermissionOk)


def test_external_permission_table_can_restrict_a_non_invariant_type():
    permission_table = {InterventionType.WORLD_DIRECTIVE: frozenset({"full_gm", "god"})}
    result = check_permission(InterventionType.WORLD_DIRECTIVE, "watcher", permission_table)
    assert isinstance(result, PermissionRejection)
    assert result.requested_user_mode == "watcher"
