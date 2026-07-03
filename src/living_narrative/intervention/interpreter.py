"""Intervention Interpreter (spec.md Requirement "Intervention Interpreterによる自由文解釈").

Calls llm-provider's structured output via binding key ``interpreter`` (spec-foundation D122)
and turns each returned ``InterventionDraft`` into a validated ``Intervention`` (or a typed
rejection) through the same ``finalize_draft`` used by the direct-input path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from living_narrative.intervention.build import finalize_draft
from living_narrative.intervention.permissions import PermissionRejection, PermissionTable
from living_narrative.intervention.schema import Intervention, InterventionDraft
from living_narrative.state.models import UserMode

if TYPE_CHECKING:
    # Only for the type hint: importing this eagerly would import ``pipeline``, which (via
    # ``pipeline.driver`` -> ``intervention.service``) cycles back to this module.
    from living_narrative.pipeline.llm_gateway import LLMGateway

PROMPT_TEMPLATE_NAME = "intervention-interpreter-v1"

SYSTEM_PROMPT = (
    "Decompose the user's free-text instruction into one or more structured interventions, "
    "one of the 15 known intervention types each. Never silently drop part of the input: if a "
    "fragment does not clearly match any other known type, classify it as scene_directive and "
    "keep its original wording in content. Do not invent id, turn, or user_role fields — they "
    "are not part of the response schema."
)


class InterpreterOutput(BaseModel):
    interventions: list[InterventionDraft]
    confidence: float = Field(ge=0.0, le=1.0)
    interpretation_summary: str


@dataclass
class InterpreterResult:
    interventions: list[Intervention] = field(default_factory=list)
    rejections: list[PermissionRejection] = field(default_factory=list)
    confidence: float = 0.0
    interpretation_summary: str = ""


def build_interpreter_messages(free_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": free_text},
    ]


def interpret_free_text(
    gateway: LLMGateway,
    free_text: str,
    *,
    turn: int,
    user_role: UserMode,
    allocate_id: Callable[[], str],
    permission_table: PermissionTable | None = None,
) -> InterpreterResult:
    messages = build_interpreter_messages(free_text)
    output = gateway.complete(
        "interpreter", messages, InterpreterOutput, prompt_template_name=PROMPT_TEMPLATE_NAME
    )
    assert isinstance(output, InterpreterOutput)

    result = InterpreterResult(
        confidence=output.confidence, interpretation_summary=output.interpretation_summary
    )
    for draft in output.interventions:
        outcome = finalize_draft(
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
