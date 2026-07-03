"""Mechanical continuity checker."""

from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.registry import Finding
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import CharacterStatus, Event


def continuity_checker(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[Finding]:
    del narration_text
    active = set()
    for scene in context.bundle.scenes:
        if scene.status == "active":
            active.update(scene.active_characters)
    status = {character.id: character.status for character in context.bundle.characters}
    findings: list[Finding] = []
    for event in resolved_events:
        character_id = event.effects.get("character_id")
        if not character_id:
            continue
        if character_id not in active:
            findings.append(_finding("absent character acted", character_id, event.id))
        if status.get(character_id) in {CharacterStatus.DEAD, CharacterStatus.MISSING}:
            findings.append(_finding("dead or missing character acted", character_id, event.id))
        if event.type.endswith("dialogue") and character_id not in active:
            findings.append(_finding("non-present character spoke", character_id, event.id))
    for change in diff_candidate.changes:
        if (
            change.target == "character"
            and change.op == "add"
            and "knowledge" in change.path
            and change.source_event is None
        ):
            findings.append(
                _finding("knowledge addition missing source_event", change.id or "", "")
            )
    return findings


def llm_canon_evaluation(enabled: bool) -> list[Finding]:
    if not enabled:
        return []
    return [
        Finding(
            checker="continuity",
            severity="warn",
            message="heuristic LLM canon consistency evaluation requested",
            related_ids=[],
        )
    ]


def _finding(message: str, character_id: str, event_id: str) -> Finding:
    return Finding(
        checker="continuity",
        severity="error",
        message=message,
        related_ids=[item for item in (character_id, event_id) if item],
    )
