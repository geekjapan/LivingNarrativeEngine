"""Renderer registry (D108): built-in narration output styles."""

import re
from collections.abc import Callable
from typing import Any

from living_narrative.narration.models import NarratorContext

RendererFunc = Callable[[NarratorContext, str, str | None], str]

_NO_EVENTS_NOVEL = "特に目立った出来事のない、静かな一幕だった。"
_NO_EVENTS_LOG = "特筆すべき出来事はなかった。"
_CHARACTER_ID = re.compile(r"^char_\d+$")


class RendererNotFoundError(KeyError):
    def __init__(self, name: str) -> None:
        super().__init__(f"no renderer registered for style {name!r}")


class RendererRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, RendererFunc] = {}

    def register(self, name: str, renderer: RendererFunc) -> None:
        self._renderers[name] = renderer

    def contains(self, name: str) -> bool:
        return name in self._renderers

    def copy(self) -> "RendererRegistry":
        registry = RendererRegistry()
        registry._renderers = self._renderers.copy()
        return registry

    def get(self, name: str) -> RendererFunc:
        try:
            return self._renderers[name]
        except KeyError as exc:
            raise RendererNotFoundError(name) from exc


# Trailing chars that already close a sentence — appending 。 double-punctuates (…。 」。 ）。).
_SENTENCE_CLOSERS = ("。", "、", "！", "？", "…", "‥", "」", "』", "）", ")")


def _sentence(text: str) -> str:
    return text if text.endswith(_SENTENCE_CLOSERS) else f"{text}。"


def novel_renderer(context: NarratorContext, mood: str, tone_control: str | None) -> str:
    sentences: list[Any] = []
    if mood:
        sentences.append(_sentence(f"{mood}の空気が漂っている"))
    sentences.extend(_sentence(fact) for fact in context.scene_reader_visible_facts)
    sentences.extend(_sentence(event.text) for event in context.reader_visible_events)
    if not sentences:
        sentences.append(_NO_EVENTS_NOVEL)
    return "".join(sentences)


def log_renderer(context: NarratorContext, mood: str, tone_control: str | None) -> str:
    lines = [f"# turn {context.turn}"]
    if mood:
        lines.append(f"- mood: {mood}")
    lines.extend(f"- fact: {fact}" for fact in context.scene_reader_visible_facts)
    lines.extend(f"- event[{event.type}]: {event.text}" for event in context.reader_visible_events)
    if len(lines) == 1:
        lines.append(f"- {_NO_EVENTS_LOG}")
    return "\n".join(lines)


def vn_renderer(context: NarratorContext, mood: str, tone_control: str | None) -> str:
    """Render reader-visible context as deterministic, line-oriented VN script source."""
    lines = [f"# turn {context.turn}"]
    if context.scene_summary:
        lines.append(f"# BACKGROUND: {context.scene_summary}")
    if mood:
        lines.append(f"# BGM: {mood}")
    lines.extend(f"NARRATOR: {fact}" for fact in context.scene_reader_visible_facts)
    for event in context.reader_visible_events:
        raw_character_id = event.effects.get("character_id")
        character_id = (
            raw_character_id
            if isinstance(raw_character_id, str) and _CHARACTER_ID.fullmatch(raw_character_id)
            else None
        )
        if character_id:
            lines.append(f"# SPRITE: {character_id}")
        if event.effects.get("sfx"):
            lines.append(f"# SFX: {event.effects['sfx']}")
        if event.type.endswith("dialogue") or event.type == "dialogue":
            speaker = character_id or "UNKNOWN"
            lines.append(f"{speaker}: {event.text}")
        else:
            lines.append(f"NARRATOR: {event.text}")
    if len(lines) == 1:
        lines.append(f"NARRATOR: {_NO_EVENTS_NOVEL}")
    return "\n".join(lines)


def default_renderer_registry() -> RendererRegistry:
    registry = RendererRegistry()
    registry.register("novel", novel_renderer)
    registry.register("log", log_renderer)
    registry.register("vn", vn_renderer)
    return registry
