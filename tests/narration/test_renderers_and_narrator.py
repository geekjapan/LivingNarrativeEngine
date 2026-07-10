import re

import pytest

from living_narrative.narration import (
    NarratorContext,
    RendererNotFoundError,
    default_renderer_registry,
    narrate,
)
from living_narrative.state.models import Event, Visibility

_JAPANESE_RE = re.compile(r"[぀-ヿ一-鿿]")


def _context() -> NarratorContext:
    return NarratorContext(
        turn=3,
        reader_state_facts=["既知の事実"],
        scene_reader_visible_facts=["駅は静かだ"],
        reader_visible_events=[
            Event(
                id="event_0001",
                turn=3,
                type="action",
                text="彼は歩き出した",
                visibility=Visibility.READER,
            )
        ],
    )


def test_novel_renderer_produces_continuous_japanese_prose():
    result = narrate(_context(), style="novel", mood="緊張")

    assert result.style == "novel"
    assert result.text
    assert _JAPANESE_RE.search(result.text)
    assert "駅は静かだ" in result.text
    assert "彼は歩き出した" in result.text


def test_log_renderer_produces_bulleted_log():
    result = narrate(_context(), style="log")

    assert result.style == "log"
    assert result.text.startswith("# turn 3")
    assert "- fact: 駅は静かだ" in result.text
    assert "- event[action]: 彼は歩き出した" in result.text


def test_vn_renderer_is_registered_without_changing_existing_defaults():
    context = NarratorContext(
        turn=3,
        scene_summary="夜の駅",
        reader_visible_events=[
            Event(
                id="event_0001",
                turn=3,
                type="character_dialogue",
                text="「行こう」",
                visibility=Visibility.READER,
                effects={"character_id": "char_001", "sfx": "足音"},
            )
        ],
    )

    result = narrate(context, style="vn", mood="緊張")

    assert result.style == "vn"
    assert "# BACKGROUND: 夜の駅" in result.text
    assert "# BGM: 緊張" in result.text
    assert "# SPRITE: char_001" in result.text
    assert "# SFX: 足音" in result.text
    assert "char_001: 「行こう」" in result.text
    assert narrate(_context(), style="novel").style == "novel"


def test_vn_renderer_does_not_emit_invalid_sprite_reference():
    context = NarratorContext(
        turn=1,
        reader_visible_events=[
            Event(
                id="event_0001",
                turn=1,
                type="character_dialogue",
                text="声だけが響く",
                visibility=Visibility.READER,
                effects={"character_id": "intruder"},
            )
        ],
    )

    result = narrate(context, style="vn")

    assert "# SPRITE:" not in result.text
    assert "UNKNOWN: 声だけが響く" in result.text


def test_narrator_falls_back_to_default_message_without_events_or_facts():
    empty_context = NarratorContext(turn=1)

    result = narrate(empty_context, style="novel")

    assert result.text
    assert _JAPANESE_RE.search(result.text)


def test_novel_renderer_does_not_double_punctuate():
    context = NarratorContext(
        turn=1,
        reader_visible_events=[
            Event(
                id="event_0001",
                turn=1,
                type="action",
                text="足音が遠ざかっていく…",
                visibility=Visibility.READER,
            ),
            Event(
                id="event_0002",
                turn=1,
                type="action",
                text="彼女は頷いた(小さく)",
                visibility=Visibility.READER,
            ),
            Event(
                id="event_0003",
                turn=1,
                type="dialogue",
                text="「行こう」",
                visibility=Visibility.READER,
            ),
        ],
    )

    result = narrate(context, style="novel")

    assert "…。" not in result.text
    assert ")。" not in result.text
    assert "」。" not in result.text


def test_unregistered_renderer_style_raises():
    with pytest.raises(RendererNotFoundError):
        narrate(_context(), style="script")


def test_tone_control_value_is_passed_through_to_renderer():
    captured = {}

    def spy_renderer(context, mood, tone_control):
        captured["mood"] = mood
        captured["tone_control"] = tone_control
        return "captured"

    registry = default_renderer_registry()
    registry.register("spy", spy_renderer)

    narrate(_context(), style="spy", mood="静寂", tone_control="serious", registry=registry)

    assert captured == {"mood": "静寂", "tone_control": "serious"}
