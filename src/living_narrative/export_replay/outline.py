"""Deterministic chapter outline construction from ``SessionReconstruction`` (docs/issues/027).

No LLM calls. Chapter boundary rule:

- One chapter per scene by default.
- A scene whose turn span exceeds ``_LONG_SCENE_TURN_THRESHOLD`` (8 turns) is split further,
  but *only* at turns where a ``TurningPoint`` from the reconstruction actually lands inside the
  scene (design's "長いシーンは転換点で分割" — split points are never invented). A long scene with
  no interior turning point is therefore left as a single (possibly >8-turn) chapter; this is the
  one case where the "aim 3〜8 turns/chapter" target is not guaranteed.
- A candidate split at turn *t* is only taken if the segment it would close
  (``current_start..t-1``) is at least ``_MIN_CHAPTER_TURNS`` (3) turns long, so back-to-back
  turning points don't produce degenerate near-empty chapters. The final segment of a scene is
  always emitted regardless of its length (it may end up shorter than 3 turns if the scene's end
  doesn't land on a 3-turn boundary past the last split).

Chapter titles are mechanical: ``"{scene.location} — {description}"`` where ``description`` is
the turning point landing exactly on ``chapter.start_turn`` (by construction, every chapter
boundary other than the very first chapter of the whole session is exactly a turning point's
turn — either the scene-transition that started the scene, or an interior split point), falling
back to the chapter's first key event's text, and finally to the bare ``location`` if neither
exists (this only ever happens for the first chapter of ``scene_001``, whose start is assumed
rather than evidenced — see ``reconstruction.py``'s module docstring).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from living_narrative.export_replay.loader import TurnRecord
from living_narrative.export_replay.reconstruction import (
    KeyEvent,
    SessionReconstruction,
    TurningPoint,
)

_LONG_SCENE_TURN_THRESHOLD = 8
_MIN_CHAPTER_TURNS = 3


class Chapter(BaseModel):
    index: int
    title: str
    scene_id: str
    start_turn: int
    end_turn: int
    key_events: list[KeyEvent] = Field(default_factory=list)
    narration_texts: list[str] = Field(default_factory=list)


class Outline(BaseModel):
    chapters: list[Chapter] = Field(default_factory=list)


def narration_by_turn_from_records(records: list[TurnRecord]) -> dict[int, str]:
    """Reader-visible narration bodies keyed by turn, body turns only — the same
    ``is_body_turn`` gate ``render_novel``/``render_log`` use for replay export."""
    return {record.turn: record.narration_body or "" for record in records if record.is_body_turn}


def build_outline(
    reconstruction: SessionReconstruction, narration_by_turn: dict[int, str]
) -> Outline:
    """Derive a chapter outline from a scene reconstruction plus that reconstruction's
    narration bodies (see ``narration_by_turn_from_records``).

    ``reconstruction`` should come from ``reconstruct_session`` in its default reader mode
    (``include_gm=False``) — outline/novel export is a reader-facing artifact, so this
    function never re-filters visibility itself; it trusts whatever scenes/key_events it is
    handed.
    """
    last_turn = max(narration_by_turn) if narration_by_turn else None
    turning_point_description_by_turn: dict[int, str] = {}
    for point in reconstruction.turning_points:
        turning_point_description_by_turn.setdefault(point.turn, point.description)

    chapters: list[Chapter] = []
    for scene in reconstruction.scenes:
        end_turn = scene.end_turn if scene.end_turn is not None else (last_turn or scene.start_turn)
        for start, end in _split_scene(scene.start_turn, end_turn, reconstruction.turning_points):
            key_events = [event for event in scene.key_events if start <= event.turn <= end]
            # Chapters must partition turns: a scene-transition turn belongs to the
            # *outgoing* scene's chapter (matching reconstruction.py's key-event
            # attribution), so clamp this chapter's start past the previous chapter.
            if chapters:
                effective_start = max(start, chapters[-1].end_turn + 1)
            else:
                effective_start = start
            if effective_start > end:
                # Empty range — drop the chapter, attach its key_events to the previous one.
                chapters[-1].key_events.extend(key_events)
                continue
            title = _chapter_title(
                scene.location, turning_point_description_by_turn, start, key_events
            )
            overflow = [event for event in key_events if event.turn < effective_start]
            if overflow:
                chapters[-1].key_events.extend(overflow)
                key_events = [event for event in key_events if event.turn >= effective_start]
            start = effective_start
            narration_texts = [
                narration_by_turn[turn]
                for turn in range(start, end + 1)
                if turn in narration_by_turn
            ]
            chapters.append(
                Chapter(
                    index=len(chapters) + 1,
                    title=title,
                    scene_id=scene.id,
                    start_turn=start,
                    end_turn=end,
                    key_events=key_events,
                    narration_texts=narration_texts,
                )
            )
    return Outline(chapters=chapters)


def render_outline_markdown(outline: Outline) -> str:
    """Human-readable ``outline.md``: a heading per chapter with its turn range/key_events."""
    lines = ["# 章立て", ""]
    for chapter in outline.chapters:
        lines.append(f"## 第{chapter.index}章: {chapter.title}")
        lines.append(f"- シーン: {chapter.scene_id}")
        lines.append(f"- ターン: {chapter.start_turn}〜{chapter.end_turn}")
        if chapter.key_events:
            lines.append("- key_events:")
            lines.extend(
                f"  - ターン{event.turn} [{event.type}] {event.text}"
                for event in chapter.key_events
            )
        else:
            lines.append("- key_events: (なし)")
        lines.append(f"- narration素材: {len(chapter.narration_texts)}ターン分")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


# --- internal helpers --------------------------------------------------------


def _split_scene(start: int, end: int, turning_points: list[TurningPoint]) -> list[tuple[int, int]]:
    if end - start + 1 <= _LONG_SCENE_TURN_THRESHOLD:
        return [(start, end)]

    split_turns = sorted({point.turn for point in turning_points if start < point.turn <= end})
    ranges: list[tuple[int, int]] = []
    current_start = start
    for turn in split_turns:
        if turn - current_start >= _MIN_CHAPTER_TURNS:
            ranges.append((current_start, turn - 1))
            current_start = turn
    ranges.append((current_start, end))
    return ranges


def _chapter_title(
    location: str,
    turning_point_description_by_turn: dict[int, str],
    start_turn: int,
    key_events: list[KeyEvent],
) -> str:
    description = turning_point_description_by_turn.get(start_turn)
    if description:
        return f"{location} — {description}"
    if key_events:
        return f"{location} — {key_events[0].text}"
    return location
