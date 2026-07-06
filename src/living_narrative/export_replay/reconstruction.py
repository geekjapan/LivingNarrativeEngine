"""Deterministic scene reconstruction from turn artifacts + final state (docs/issues/026).

No LLM calls: scene boundaries are recovered from ``state_diff.yaml``'s ``target=scene,
path=status`` changes (Issue 009's scene-transition mechanism), key events are picked out of
each body turn's ``events.yaml`` by a fixed whitelist of "plot-turning" event types, and a
scene's displayed ``location``/``mood``/``summary`` are its *final* values from current state
(no per-turn replay of scene-field edits — the "final value" simplification docs/issues/026
calls for).

Reuses (does not re-implement) two contracts already established by this package:
- ``TurnRecord.is_body_turn``: a turn only counts if ``applied`` and not a ``reject_all``
  review resolution (spec-foundation.md §9 D120) — the same gate ``assemble_replay`` uses.
- reader-visibility philosophy: reader mode never sees a ``gm_only``-tagged key event.
  ``thread_update`` events are always emitted ``gm_only`` (``state_manager._thread_update_
  changes``), so in practice they only ever surface in ``--gm``/``include_gm=True`` mode.

**Known limitation** (design assumption, docs/issues/026): only ``scene_001`` is assumed
active from turn 1 with no turn evidence required. Any other scene pre-configured as
``active`` in the *initial* state (rather than reached via a recorded transition) has no
turn evidence and is silently omitted from the reconstruction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from living_narrative.export_replay.loader import TurnRecord, load_turn_records
from living_narrative.state.store import StateLoadError, StateStore
from living_narrative.workspace.loader import load_project

_SCENE_ONE_ID = "scene_001"

# Event kinds a key event can classify to. Anything else (background_event, threat_pressure,
# pacing_stall, dice_roll_request, ...) is deliberately excluded as per-turn noise.
_TURNING_POINT_KINDS = frozenset({"threat_stage", "scene_transition"})


class ReconstructionError(RuntimeError):
    """The project at the given path could not be loaded (invalid config/state)."""


class KeyEvent(BaseModel):
    turn: int
    type: str
    text: str
    visibility: str


class SceneRecord(BaseModel):
    id: str
    location: str
    mood: str
    summary: str
    start_turn: int
    end_turn: int | None = None
    key_events: list[KeyEvent] = Field(default_factory=list)


class TurningPoint(BaseModel):
    turn: int
    kind: str
    description: str


class SessionReconstruction(BaseModel):
    scenes: list[SceneRecord] = Field(default_factory=list)
    turning_points: list[TurningPoint] = Field(default_factory=list)


def reconstruct_session(project_path: Path, include_gm: bool = False) -> SessionReconstruction:
    """Rebuild the scene timeline + key events/turning points for the project at
    ``project_path`` (a ``project.yaml``).

    ``include_gm=True`` additionally surfaces ``gm_only``-tagged key events/turning points
    (e.g. ``thread_update``); the default reader mode drops them, mirroring
    ``export_replay``'s reader-visibility contract.

    Raises ``ReconstructionError`` if the project config/required state files are missing or
    invalid (mirrors ``session.metrics.collect_metrics``'s error handling).
    """
    if not project_path.exists():
        raise ReconstructionError(f"project not found: {project_path}")

    result = load_project(project_path)
    if not result.is_valid:
        if result.errors:
            details = "; ".join(f"{issue.field}: {issue.message}" for issue in result.errors)
        else:
            details = f"missing state files: {', '.join(result.missing_state_files)}"
        raise ReconstructionError(f"invalid project at {project_path}: {details}")

    try:
        bundle = StateStore.load(result.paths.state)
    except StateLoadError as exc:
        details = "; ".join(f"{issue.file_path}: {issue.message}" for issue in exc.issues)
        raise ReconstructionError(f"invalid state at {result.paths.state}: {details}") from exc

    records = load_turn_records(result.paths.runs)
    scenes_by_id = {scene.id: scene for scene in bundle.scenes}

    starts, ends = _scene_boundaries(records, scenes_by_id)
    scene_order = sorted(starts, key=lambda scene_id: (starts[scene_id], scene_id))
    scene_records = [
        SceneRecord(
            id=scene_id,
            location=scenes_by_id[scene_id].location,
            mood=scenes_by_id[scene_id].mood,
            summary=scenes_by_id[scene_id].summary,
            start_turn=starts[scene_id],
            end_turn=ends.get(scene_id),
        )
        for scene_id in scene_order
    ]

    turning_points: list[TurningPoint] = []
    for record in records:
        for event in _body_events(record):
            kind = _classify_event(event)
            if kind is None:
                continue
            visibility = event.get("visibility") or ""
            if not include_gm and visibility == "gm_only":
                continue
            key_event = KeyEvent(
                turn=record.turn, type=kind, text=event.get("text") or "", visibility=visibility
            )
            scene = scene_for_turn(scene_records, record.turn)
            if scene is not None:
                scene.key_events.append(key_event)
            if kind in _TURNING_POINT_KINDS:
                turning_points.append(
                    TurningPoint(turn=record.turn, kind=kind, description=key_event.text)
                )
        if record.status == "stopped_for_review":
            turning_points.append(
                TurningPoint(
                    turn=record.turn,
                    kind="review_stop",
                    description=f"ターン{record.turn}: レビューのため停止",
                )
            )

    return SessionReconstruction(scenes=scene_records, turning_points=turning_points)


def render_scenes_markdown(reconstruction: SessionReconstruction) -> str:
    """Human-readable ``scenes.md``: a heading per scene (period/summary/key_events) plus a
    trailing 転換点 (turning points) section."""
    lines = ["# シーン一覧", ""]
    for scene in reconstruction.scenes:
        end_label = str(scene.end_turn) if scene.end_turn is not None else "継続中"
        lines.append(f"## シーン: {scene.location} ({scene.id})")
        lines.append(f"- 期間: ターン{scene.start_turn}〜{end_label}")
        lines.append(f"- summary: {scene.summary}")
        if scene.key_events:
            lines.append("- key_events:")
            lines.extend(
                f"  - ターン{event.turn} [{event.type}] {event.text} ({event.visibility})"
                for event in scene.key_events
            )
        else:
            lines.append("- key_events: (なし)")
        lines.append("")

    lines.append("## 転換点")
    if reconstruction.turning_points:
        lines.extend(
            f"- ターン{point.turn} [{point.kind}] {point.description}"
            for point in reconstruction.turning_points
        )
    else:
        lines.append("(なし)")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


# --- internal helpers --------------------------------------------------------


def _body_events(record: TurnRecord) -> list[dict[str, Any]]:
    return record.events if record.is_body_turn else []


def _body_diff_changes(record: TurnRecord) -> list[dict[str, Any]]:
    if not record.is_body_turn or not record.diff or not record.diff.get("applied"):
        return []
    return list((record.diff.get("diff") or {}).get("changes") or [])


def _scene_boundaries(
    records: list[TurnRecord], scenes_by_id: dict[str, Any]
) -> tuple[dict[str, int], dict[str, int]]:
    """``(starts, ends)`` scene_id -> turn, recovered from ``target=scene, path=status``
    diff changes, plus the design's hardcoded ``scene_001`` starts-at-turn-1 assumption."""
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    if _SCENE_ONE_ID in scenes_by_id:
        starts[_SCENE_ONE_ID] = 1
    for record in records:
        for change in _body_diff_changes(record):
            if (
                change.get("target") != "scene"
                or change.get("op") != "set"
                or change.get("path") != "status"
            ):
                continue
            scene_id = change.get("id")
            if not scene_id:
                continue
            value = change.get("value")
            if value == "active":
                starts.setdefault(scene_id, record.turn)
            elif value == "ended":
                ends.setdefault(scene_id, record.turn)
    return starts, ends


def _classify_event(event: dict[str, Any]) -> str | None:
    """Whitelist of "plot-turning" event kinds a key event can be. Mirrors the same
    predicates ``agents.state_manager._changes_for_event``/``_thread_update_changes`` use to
    detect these event shapes, so classification never drifts from what actually mutates
    state. Returns ``None`` for per-turn noise (background_event, threat_pressure, ...)."""
    event_type = event.get("type")
    effects = event.get("effects") or {}
    if event_type == "threat_stage":
        return "threat_stage"
    if (
        effects.get("scene_transition")
        or effects.get("scene_status") == "ended"
        or event_type == "scene_end"
    ):
        return "scene_transition"
    if event_type == "reveal_control":
        return "reveal_control"
    if event_type == "thread_update":
        return "thread_update"
    if event_type == "character_death" or effects.get("status") == "dead":
        return "character_death"
    return None


def scene_for_turn(scene_records: list[SceneRecord], turn: int) -> SceneRecord | None:
    """The scene active during ``turn``. Scene-transition turns have both the outgoing
    scene's ``end_turn`` and the incoming scene's ``start_turn`` equal to that turn; iterating
    in ascending ``start_turn`` order and returning the first match attributes the boundary
    turn's key events to the *outgoing* scene (the one the transition concludes).

    Public: reused by ``export_replay/trpg.py`` (Issue 028) to group turns under scene
    headings without re-deriving scene-membership logic."""
    for scene in scene_records:
        if scene.start_turn <= turn and (scene.end_turn is None or turn <= scene.end_turn):
            return scene
    return None
