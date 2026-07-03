"""Role permission hook (design.md D2): hardcoded universal invariants + pluggable table."""

from pydantic import BaseModel

from living_narrative.intervention.schema import InterventionType
from living_narrative.state.models import UserMode

PermissionTable = dict[InterventionType, frozenset[UserMode]]

# The only permission facts this capability hardcodes (D107/D114): everything else is data
# supplied by the caller (ultimately owned by session-autonomy).
_UNIVERSAL_INVARIANTS: dict[InterventionType, frozenset[UserMode]] = {
    InterventionType.CANON_EDIT: frozenset({"full_gm", "god"}),
    InterventionType.HIDDEN_TRUTH_EDIT: frozenset({"full_gm", "god"}),
}


class PermissionOk(BaseModel):
    pass


class PermissionRejection(BaseModel):
    type: InterventionType
    requested_user_mode: UserMode
    allowed_user_modes: list[UserMode]


PermissionResult = PermissionOk | PermissionRejection


def default_permission_table() -> PermissionTable:
    """Permissive default (spec.md Requirement "Role Permission Hook"): no table supplied."""
    return {}


def check_permission(
    intervention_type: InterventionType,
    user_mode: UserMode,
    permission_table: PermissionTable | None = None,
) -> PermissionResult:
    invariant = _UNIVERSAL_INVARIANTS.get(intervention_type)
    if invariant is not None and user_mode not in invariant:
        return PermissionRejection(
            type=intervention_type,
            requested_user_mode=user_mode,
            allowed_user_modes=sorted(invariant),
        )

    allowed = (permission_table or {}).get(intervention_type)
    if allowed is not None and user_mode not in allowed:
        return PermissionRejection(
            type=intervention_type,
            requested_user_mode=user_mode,
            allowed_user_modes=sorted(allowed),
        )
    return PermissionOk()
