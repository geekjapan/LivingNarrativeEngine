"""``intervention`` capability: schema, permissions, Interpreter, direct input, routing, history.

Note: ``interpreter`` and ``service`` are deliberately NOT re-exported here even though they're
part of the public surface — both import ``pipeline.llm_gateway``, and ``pipeline`` imports
``narration``/``agents`` modules that import this package (for ``reveal``/``router``). Eagerly
importing them here would make this package's import order-sensitive to a cycle. Import them
directly: ``from living_narrative.intervention.service import run_intervene_phase``.
"""

from living_narrative.intervention.build import finalize_draft
from living_narrative.intervention.direct_input import build_intervention_from_direct_input
from living_narrative.intervention.history import (
    InterventionHistory,
    InterventionHistoryEntry,
    append_history,
    build_history_entries,
    load_history,
    mark_superseded_by_rerun,
)
from living_narrative.intervention.ids import make_intervention_id_allocator
from living_narrative.intervention.permissions import (
    PermissionOk,
    PermissionRejection,
    PermissionTable,
    check_permission,
    default_permission_table,
)
from living_narrative.intervention.reveal import (
    must_not_reveal_texts,
    reveal_now_sources,
)
from living_narrative.intervention.router import character_directives_for, resolve_tone_control
from living_narrative.intervention.schema import (
    HANDLING_STATUS,
    HandlingStatus,
    Intervention,
    InterventionDraft,
    InterventionTarget,
    InterventionType,
)

__all__ = [
    "HANDLING_STATUS",
    "HandlingStatus",
    "Intervention",
    "InterventionDraft",
    "InterventionHistory",
    "InterventionHistoryEntry",
    "InterventionTarget",
    "InterventionType",
    "PermissionOk",
    "PermissionRejection",
    "PermissionTable",
    "append_history",
    "build_history_entries",
    "build_intervention_from_direct_input",
    "character_directives_for",
    "check_permission",
    "default_permission_table",
    "finalize_draft",
    "load_history",
    "make_intervention_id_allocator",
    "mark_superseded_by_rerun",
    "must_not_reveal_texts",
    "resolve_tone_control",
    "reveal_now_sources",
]
