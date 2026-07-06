"""Character-consistency checker (Issue 016): warns, never blocks, when a character's own
dialogue/action text either (a) mentions something that character's ``knowledge.does_not_know``
says they don't know, or (b) discloses one of their own ``secrets`` in a reader-visible event.

Both rules are speaker-scoped: other characters' ``does_not_know``/``secrets`` entries never
apply to a different character's line (inner thoughts touching a secret via ``character``/
``gm_only``/``scene`` visibility are normal and not flagged -- only ``reader``-visible
disclosure is)."""

from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.registry import Finding
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event, Visibility

_SPEAKER_EVENT_TYPES = {"character_dialogue", "character_action"}


def character_consistency_checker(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[Finding]:
    del narration_text, diff_candidate
    characters_by_id = {character.id: character for character in context.bundle.characters}
    findings: list[Finding] = []
    for event in resolved_events:
        if event.type not in _SPEAKER_EVENT_TYPES:
            continue
        character_id = event.effects.get("character_id")
        if not character_id:
            continue
        character = characters_by_id.get(character_id)
        if character is None:
            continue

        for item in character.knowledge.does_not_know:
            if item in event.text:
                findings.append(
                    Finding(
                        checker="character_consistency_check",
                        severity="warn",
                        message=(
                            f"{character.name}({character_id})が知らないはずの「{item}」に"
                            "言及しています"
                        ),
                        related_ids=[event.id],
                    )
                )

        if event.visibility != Visibility.READER:
            continue
        for secret in character.secrets:
            if secret in event.text:
                findings.append(
                    Finding(
                        checker="character_consistency_check",
                        severity="warn",
                        message=(
                            f"{character.name}({character_id})が自分の秘密「{secret}」を"
                            "開示しています"
                        ),
                        related_ids=[event.id],
                    )
                )
    return findings
