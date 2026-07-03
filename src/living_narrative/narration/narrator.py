"""Narrator: renders a ``NarratorContext`` through a registered renderer style."""

from living_narrative.narration.models import NarrationResult, NarratorContext
from living_narrative.narration.renderers import RendererRegistry, default_renderer_registry


def narrate(
    context: NarratorContext,
    *,
    style: str,
    mood: str = "",
    tone_control: str | None = None,
    registry: RendererRegistry | None = None,
) -> NarrationResult:
    registry = registry or default_renderer_registry()
    renderer = registry.get(style)
    text = renderer(context, mood, tone_control)
    return NarrationResult(text=text, style=style)
