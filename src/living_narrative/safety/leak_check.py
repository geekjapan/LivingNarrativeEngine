"""Mechanical leak checker."""

import re
import unicodedata

from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.registry import Finding
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event, Visibility


def leak_checker(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[Finding]:
    text = _normalize(" ".join([narration_text, *_reader_event_texts(resolved_events)]))
    allowed = {_normalize(item) for item in _allowed_reveals(context, diff_candidate)}
    findings: list[Finding] = []
    for fact in context.bundle.gm_vault:
        if _normalize(fact.id) in text:
            findings.append(
                Finding(
                    checker="leak",
                    severity="error",
                    message=f"gm_vault fact id leaked: {fact.id}",
                    related_ids=[fact.id],
                )
            )
    for fact in _secret_texts(context):
        normalized = _normalize(fact[1])
        if normalized and normalized in text and normalized not in allowed:
            findings.append(
                Finding(
                    checker="leak",
                    severity="error",
                    message="hidden or private text leaked",
                    related_ids=[fact[0]],
                )
            )
    return findings


def llm_leak_evaluation(enabled: bool) -> list[Finding]:
    if not enabled:
        return []
    return [
        Finding(
            checker="leak",
            severity="warn",
            message="heuristic LLM leak evaluation requested",
            related_ids=[],
        )
    ]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold())


def _reader_event_texts(events: list[Event]) -> list[str]:
    return [event.text for event in events if event.visibility == Visibility.READER]


def _secret_texts(context: TurnContext) -> list[tuple[str, str]]:
    facts: list[tuple[str, str]] = []
    for scene in context.bundle.scenes:
        facts.extend((fact.id, fact.text) for fact in scene.hidden_facts)
    for character in context.bundle.characters:
        facts.extend((character.id, text) for text in character.secrets)
        facts.extend((character.id, text) for text in character.private_mind)
    return facts


def _allowed_reveals(context: TurnContext, diff: StateDiff) -> list[str]:
    existing = [entry.text for entry in context.bundle.reader_state]
    added = [
        change.value.get("text")
        for change in diff.changes
        if change.target == "reader_state"
        and change.op == "add"
        and isinstance(change.value, dict)
        and change.value.get("text")
    ]
    return [*existing, *added]
