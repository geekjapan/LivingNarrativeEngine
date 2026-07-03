"""Pipeline-facing Intervene-phase entry point (spec-foundation.md §6 phase 2).

Combines the Interpreter (free text) and direct-input (structured) paths, both subject to the
same permission hook, into the single list the turn-pipeline persists to ``intervention.yaml``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from living_narrative.intervention.direct_input import build_intervention_from_direct_input
from living_narrative.intervention.interpreter import interpret_free_text
from living_narrative.intervention.permissions import PermissionRejection, PermissionTable
from living_narrative.intervention.schema import Intervention
from living_narrative.state.models import UserMode

if TYPE_CHECKING:
    # Only for the type hint: importing this eagerly would import ``pipeline``, which (via
    # ``pipeline.driver``) imports this module — see interpreter.py for the same pattern.
    from living_narrative.pipeline.llm_gateway import LLMGateway


@dataclass
class InterveneResult:
    interventions: list[Intervention] = field(default_factory=list)
    rejections: list[PermissionRejection] = field(default_factory=list)


def run_intervene_phase(
    *,
    gateway: LLMGateway,
    turn: int,
    user_role: UserMode,
    allocate_id: Callable[[], str],
    permission_table: PermissionTable | None = None,
    free_text: str | None = None,
    direct_drafts: list[dict[str, Any]] | None = None,
) -> InterveneResult:
    result = InterveneResult()

    if free_text:
        interpreted = interpret_free_text(
            gateway,
            free_text,
            turn=turn,
            user_role=user_role,
            allocate_id=allocate_id,
            permission_table=permission_table,
        )
        result.interventions.extend(interpreted.interventions)
        result.rejections.extend(interpreted.rejections)

    for draft in direct_drafts or []:
        outcome = build_intervention_from_direct_input(
            draft,
            turn=turn,
            user_role=user_role,
            allocate_id=allocate_id,
            permission_table=permission_table,
        )
        if isinstance(outcome, PermissionRejection):
            result.rejections.append(outcome)
        else:
            result.interventions.append(outcome)

    return result
