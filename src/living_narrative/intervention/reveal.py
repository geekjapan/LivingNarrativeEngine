"""``reveal_control`` semantics (spec.md Requirement "reveal_controlの意味論", design.md D4).

Shared by the Narrator (prose-side must-not-reveal filtering) and the State Manager's
BuildDiff slot (Reader State promotion/blocking) so both sides resolve the same fact.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from living_narrative.state.models import CanonEntry, GmVaultEntry

if TYPE_CHECKING:
    # Only for type hints: importing ``pipeline.context`` at module scope would import the
    # ``pipeline`` package, which (via ``pipeline.driver`` -> ``narration`` -> this module)
    # cycles back here before this module finishes defining its own names.
    from living_narrative.pipeline.context import TurnContext


def constraint_value(item: dict[str, Any], key: str) -> Any:
    """Read ``key`` from an intervention dict, tolerating both the nested ``constraints`` shape
    and a flat top-level key (back-compat with pre-existing ad hoc intervention dicts).
    """
    if key in item:
        return item[key]
    return (item.get("constraints") or {}).get(key)


def target_id_of(item: dict[str, Any]) -> str | None:
    for key in ("target_id", "fact_id"):
        if item.get(key) is not None:
            return item[key]
    target = item.get("target") or {}
    if target.get("id") is not None:
        return target["id"]
    return constraint_value(item, "fact_id")


def find_gm_vault_or_canon_entry(
    context: TurnContext, target_id: str
) -> CanonEntry | GmVaultEntry | None:
    for entry in context.bundle.gm_vault:
        if entry.id == target_id:
            return entry
    for entry in context.bundle.canon:
        if entry.id == target_id:
            return entry
    return None


def resolve_fact_text(context: TurnContext, target_id: str | None) -> str | None:
    if target_id is None:
        return None
    entry = find_gm_vault_or_canon_entry(context, target_id)
    if entry is not None:
        return entry.text
    for scene in context.bundle.scenes:
        for fact in scene.hidden_facts:
            if fact.id == target_id:
                return fact.text
    return None


def must_not_reveal_texts(context: TurnContext, interventions: list[dict[str, Any]]) -> set[str]:
    """Every text (and raw target id, for callers that address facts by literal value) that a
    ``reveal_control``/``must-not-reveal`` intervention currently forbids surfacing to readers.
    """
    texts: set[str] = set()
    for item in interventions:
        if item.get("type") != "reveal_control":
            continue
        if constraint_value(item, "mode") != "must-not-reveal":
            continue
        target_id = target_id_of(item)
        text = resolve_fact_text(context, target_id)
        if text:
            texts.add(text)
        if target_id:
            texts.add(target_id)
    return texts


def reveal_now_sources(
    context: TurnContext, interventions: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], CanonEntry | GmVaultEntry]]:
    """``(intervention, entry)`` pairs for every resolvable ``reveal_control``/``reveal-now``."""
    pairs = []
    for item in interventions:
        if item.get("type") != "reveal_control":
            continue
        if constraint_value(item, "mode") != "reveal-now":
            continue
        target_id = target_id_of(item)
        if target_id is None:
            continue
        entry = find_gm_vault_or_canon_entry(context, target_id)
        if entry is not None:
            pairs.append((item, entry))
    return pairs
