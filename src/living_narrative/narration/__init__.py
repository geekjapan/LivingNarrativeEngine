"""Narrator, renderer registry, reader-only context extraction."""

from living_narrative.narration.context import build_narrator_context, is_reader_visible_event
from living_narrative.narration.models import NarrationResult, NarratorContext
from living_narrative.narration.narrator import narrate
from living_narrative.narration.renderers import (
    RendererNotFoundError,
    RendererRegistry,
    default_renderer_registry,
    log_renderer,
    novel_renderer,
)

__all__ = [
    "NarrationResult",
    "NarratorContext",
    "RendererNotFoundError",
    "RendererRegistry",
    "build_narrator_context",
    "default_renderer_registry",
    "is_reader_visible_event",
    "log_renderer",
    "narrate",
    "novel_renderer",
]
