"""Shared draft-to-Intervention finalization used by both the direct-input and Interpreter paths."""

from collections.abc import Callable

from living_narrative.intervention.permissions import (
    PermissionRejection,
    PermissionTable,
    check_permission,
)
from living_narrative.intervention.schema import Intervention, InterventionDraft
from living_narrative.state.models import UserMode


def finalize_draft(
    draft: InterventionDraft,
    *,
    turn: int,
    user_role: UserMode,
    allocate_id: Callable[[], str],
    permission_table: PermissionTable | None = None,
) -> Intervention | PermissionRejection:
    """Apply the role permission hook, then stamp ``id``/``turn``/``user_role`` from context.

    ``turn``/``user_role``/``allocate_id`` always come from the execution context, never from
    the draft — ``InterventionDraft`` has no such fields to begin with (spec.md Requirement
    "構造化直接入力パス").
    """
    permission_result = check_permission(draft.type, user_role, permission_table)
    if isinstance(permission_result, PermissionRejection):
        return permission_result
    return Intervention(
        id=allocate_id(),
        turn=turn,
        user_role=user_role,
        type=draft.type,
        target=draft.target,
        content=draft.content,
        constraints=draft.constraints,
        visibility=draft.visibility,
    )
