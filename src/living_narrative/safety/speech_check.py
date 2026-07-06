"""Speech-register checker (Issue 012): warns, never blocks, when a character's dialogue
uses one of that character's own ``forbidden_terms`` (e.g. the wrong first-person pronoun).
"""

from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.registry import Finding
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event


def speech_register_checker(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[Finding]:
    del narration_text, diff_candidate
    characters_by_id = {character.id: character for character in context.bundle.characters}
    findings: list[Finding] = []
    for event in resolved_events:
        if not event.type.endswith("dialogue"):
            continue
        character_id = event.effects.get("character_id")
        if not character_id:
            continue
        character = characters_by_id.get(character_id)
        if character is None:
            continue
        for term in character.speech.forbidden_terms:
            if term in event.text:
                findings.append(
                    Finding(
                        checker="speech_register_check",
                        severity="warn",
                        message=(
                            f"{character.name}({character_id})の台詞に禁止語「{term}」が含まれています"
                        ),
                        related_ids=[event.id],
                    )
                )
    return findings
