"""Structured direct-input path (spec.md Requirement "構造化直接入力パス"): no LLM call."""

from collections.abc import Callable
from typing import Any

from living_narrative.intervention.build import finalize_draft
from living_narrative.intervention.permissions import PermissionRejection, PermissionTable
from living_narrative.intervention.schema import Intervention, InterventionDraft
from living_narrative.state.models import UserMode


def build_intervention_from_direct_input(
    data: dict[str, Any],
    *,
    turn: int,
    user_role: UserMode,
    allocate_id: Callable[[], str],
    permission_table: PermissionTable | None = None,
) -> Intervention | PermissionRejection:
    """Build a validated ``Intervention`` from caller-supplied ``type``/``target``/``content``/
    ``constraints``/``visibility``.

    ``data`` may contain ``id``/``turn``/``user_role`` (e.g. a naively forwarded dict) but they
    are always ignored: ``InterventionDraft`` has no such fields, so Pydantic silently drops
    them, and the real values always come from the execution context (spec.md Scenario
    "呼び出し元が供給したuser_roleは採用されない").
    """
    draft = InterventionDraft.model_validate(data)
    return finalize_draft(
        draft,
        turn=turn,
        user_role=user_role,
        allocate_id=allocate_id,
        permission_table=permission_table,
    )
