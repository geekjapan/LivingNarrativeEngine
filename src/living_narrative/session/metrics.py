"""Regression-quality metrics aggregated from a project's on-disk artifacts/state
(docs/issues/019). Pure read-only: never mutates ``workspace/``.

Reused by ``cli/metrics.py`` (thin CLI wrapper) and, per the issue, meant to be reusable
from the web ``gm`` API later (not wired up here — that surface lives in ``web/`` and is
out of scope for this change).

**Emotion-trajectory reconstruction limitation** (design decision, see docs/issues/019):
turn artifacts only record each turn's *delta* (``state_diff.yaml``'s ``op: delta`` changes
on ``character``/``emotions.<name>``), never the character's emotion value at each point in
time. To report a min/max/ceiling-streak trajectory (not just the final value already in
``characters/*.yaml``), this module replays those per-turn deltas forward starting from the
character's ``emotions_baseline`` entry for that emotion (clamped 0-100 exactly like
``state.diff.apply_state_diff`` does). When a character has no baseline for a given emotion
(back-compat: Issue 010's decay is opt-in per emotion key), the starting point is unknown and
trajectory-derived fields (``min``/``max``/``max_consecutive_at_ceiling``) are reported as
``None`` — only ``final`` (read directly from current state) is always available. Only
``delta`` ops are replayed: no other op has ever been emitted against an ``emotions.<name>``
path in this engine (grep-verified against ``agents/state_manager.py``), so a manual ``set``
would silently not be reflected in the reconstructed trajectory.

Every metric derived from turn history (emotions, pacing, threads opened/advanced/resolved,
threat pressure/stage events, scene transitions) only considers turns whose
``state_diff.yaml`` records ``applied: true`` — this is the same flag ``state.diff`` and
``session.review`` use to mean "this turn's diff is actually reflected in current state"
(empty for a ``reject_all`` review resolution, a subset for ``partial``, unset for a turn
still awaiting review). Checker findings (``checks.yaml``) are counted across *every* live
turn regardless of ``applied``, since checks run before the commit decision and are useful
signal even on a turn that ultimately got rejected or is still pending review.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from living_narrative.pipeline.turn_numbering import (
    existing_turn_numbers,
    read_turn_status,
    turn_dir_path,
)
from living_narrative.state.models import SceneStatus, WorldStateBundle
from living_narrative.state.store import StateLoadError, StateStore
from living_narrative.workspace.loader import load_project

_DISCARDED_DIR_RE = re.compile(r"^turn_\d+_discarded_\d+$")
_ROLLEDBACK_DIR_RE = re.compile(r"^turn_\d+_rolledback_\d+$")


class MetricsError(RuntimeError):
    """The project at the given path could not be loaded (invalid config/state)."""


class TurnsMetrics(BaseModel):
    total: int
    timeline_entries: int
    by_status: dict[str, int]
    discarded: int
    rolledback: int


class EmotionMetrics(BaseModel):
    emotion: str
    final: int
    min: int | None
    max: int | None
    max_consecutive_at_ceiling: int | None


class CharacterEmotionMetrics(BaseModel):
    character_id: str
    emotions: list[EmotionMetrics]


class PacingMetrics(BaseModel):
    stall_event_count: int
    max_consecutive_stall_turns: int


class ThreadsMetrics(BaseModel):
    opened: int
    advanced: int
    resolved: int
    max_open_turns: int | None


class ThreatMetrics(BaseModel):
    threat_id: str
    initial_pressure: int | None
    final_pressure: int
    stage_fired_turns: dict[str, int]


class SceneMetrics(BaseModel):
    transition_count: int
    final_active_count: int
    final_active_scene_ids: list[str]
    final_statuses: dict[str, str]


class ChecksMetrics(BaseModel):
    by_source: dict[str, int]
    by_severity: dict[str, int]


class MemoryMetrics(BaseModel):
    summary_count: int


class GameMetrics(BaseModel):
    combat_count: int
    quest_opened: int
    quest_advanced: int
    quest_resolved: int
    applied_pc_action_count: int
    encounter_count: int
    skill_check_successes: int
    skill_check_total: int
    skill_check_success_rate: float | None


class ProjectMetrics(BaseModel):
    turns: TurnsMetrics
    emotions: list[CharacterEmotionMetrics]
    pacing: PacingMetrics
    threads: ThreadsMetrics
    threats: list[ThreatMetrics]
    scenes: SceneMetrics
    checks: ChecksMetrics
    memory: MemoryMetrics
    game: GameMetrics


def collect_metrics(project_path: Path) -> ProjectMetrics:
    """Aggregate quality metrics for the project at ``project_path`` (a ``project.yaml``).

    Raises ``MetricsError`` if the project config/required state files are missing or
    invalid (mirrors ``cli._common.load_project_or_exit``'s checks, without the typer exit).
    """
    if not project_path.exists():
        raise MetricsError(f"project not found: {project_path}")

    result = load_project(project_path)
    if not result.is_valid:
        if result.errors:
            details = "; ".join(f"{issue.field}: {issue.message}" for issue in result.errors)
        else:
            details = f"missing state files: {', '.join(result.missing_state_files)}"
        raise MetricsError(f"invalid project at {project_path}: {details}")

    try:
        bundle = StateStore.load(result.paths.state)
    except StateLoadError as exc:
        details = "; ".join(f"{issue.file_path}: {issue.message}" for issue in exc.issues)
        raise MetricsError(f"invalid state at {result.paths.state}: {details}") from exc

    live_turns = iter_live_turns(result.paths.runs)
    last_turn_number = live_turns[-1][0] if live_turns else None

    return ProjectMetrics(
        turns=_collect_turns(result.paths.runs, bundle, live_turns),
        emotions=_collect_emotions(bundle, live_turns),
        pacing=_collect_pacing(live_turns),
        threads=_collect_threads(bundle, live_turns, last_turn_number),
        threats=_collect_threats(bundle, live_turns),
        scenes=_collect_scenes(bundle, live_turns),
        checks=_collect_checks(live_turns),
        memory=MemoryMetrics(summary_count=len(bundle.memory_summaries)),
        game=_collect_game(live_turns),
    )


# --- shared loading helpers -------------------------------------------------


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def iter_live_turns(runs_dir: Path) -> list[tuple[int, Path]]:
    """Public: reused by ``export_replay/arcs.py`` (Issue 029) so its per-thread/relationship
    turn walk stays gated by the same ``applied`` semantics this module already established,
    instead of re-deriving turn iteration from scratch."""
    return [(number, turn_dir_path(runs_dir, number)) for number in existing_turn_numbers(runs_dir)]


def read_state_diff(turn_dir: Path) -> tuple[bool, list[dict[str, Any]]]:
    """``(applied, changes)`` for a turn, per the module docstring's ``applied`` gate.

    Public: reused by ``export_replay/arcs.py`` (Issue 029)."""
    data = _load_yaml(turn_dir / "state_diff.yaml")
    if not data:
        return False, []
    changes = list((data.get("diff") or {}).get("changes") or [])
    return bool(data.get("applied")), changes


def read_events(turn_dir: Path) -> list[dict[str, Any]]:
    """Public: reused by ``export_replay/arcs.py`` (Issue 029)."""
    return list(_load_yaml(turn_dir / "events.yaml") or [])


def _roll_result(turn_dir: Path, roll_id: str | None) -> int | None:
    if roll_id is None:
        return None
    for roll in _load_yaml(turn_dir / "rolls.yaml") or []:
        if roll.get("id") == roll_id:
            result = roll.get("result")
            return result if isinstance(result, int) else None
    return None


def _longest_consecutive_run(marked_turns: set[int]) -> int:
    """Longest run of *turn-number-adjacent* (``n``, ``n+1``, ...) entries in ``marked_turns``."""
    best = streak = 0
    previous: int | None = None
    for turn in sorted(marked_turns):
        streak = streak + 1 if previous is not None and turn == previous + 1 else 1
        best = max(best, streak)
        previous = turn
    return best


# --- section collectors ------------------------------------------------------


def _collect_turns(
    runs_dir: Path, bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]
) -> TurnsMetrics:
    by_status: Counter[str] = Counter()
    for _, turn_dir in live_turns:
        status = read_turn_status(turn_dir)
        by_status[status.value if status is not None else "unknown"] += 1

    discarded = rolledback = 0
    if runs_dir.exists():
        for entry in runs_dir.iterdir():
            if not entry.is_dir():
                continue
            if _DISCARDED_DIR_RE.match(entry.name):
                discarded += 1
            elif _ROLLEDBACK_DIR_RE.match(entry.name):
                rolledback += 1

    return TurnsMetrics(
        total=len(live_turns),
        timeline_entries=len(bundle.timeline),
        by_status=dict(by_status),
        discarded=discarded,
        rolledback=rolledback,
    )


def _emotion_turn_deltas(
    live_turns: list[tuple[int, Path]],
) -> dict[tuple[str, str], dict[int, int]]:
    """(character_id, emotion) -> {turn: summed delta that turn}."""
    deltas: dict[tuple[str, str], dict[int, int]] = defaultdict(dict)
    for turn, turn_dir in live_turns:
        applied, changes = read_state_diff(turn_dir)
        if not applied:
            continue
        for change in changes:
            if change.get("target") != "character" or change.get("op") != "delta":
                continue
            path = change.get("path") or ""
            if not path.startswith("emotions."):
                continue
            emotion = path[len("emotions.") :]
            key = (change.get("id"), emotion)
            bucket = deltas[key]
            bucket[turn] = bucket.get(turn, 0) + int(change.get("value") or 0)
    return deltas


def reconstruct_emotion_trajectories(
    bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]
) -> dict[tuple[str, str], list[int]]:
    """``(character_id, emotion) -> [baseline, value_after_live_turns[0], ...]``, aligned 1:1
    with ``live_turns`` (index 0 is the ``emotions_baseline`` entry, index i is the value after
    ``live_turns[i - 1]``). Only characters with a baseline for that emotion get an entry — see
    this module's docstring for why (Issue 010's decay is opt-in per emotion key).

    Public: extracted out of ``_collect_emotions`` so ``export_replay/arcs.py`` (Issue 029) can
    reuse the exact same trajectory reconstruction to report per-turn change points, instead of
    only the min/max/final summary this module needs.
    """
    deltas = _emotion_turn_deltas(live_turns)
    trajectories: dict[tuple[str, str], list[int]] = {}
    for character in bundle.characters:
        for emotion in character.emotions:
            baseline = character.emotions_baseline.get(emotion)
            if baseline is None:
                continue
            turn_deltas = deltas.get((character.id, emotion), {})
            value = baseline
            trajectory = [value]
            for turn, _ in live_turns:
                value = max(0, min(100, value + turn_deltas.get(turn, 0)))
                trajectory.append(value)
            trajectories[(character.id, emotion)] = trajectory
    return trajectories


def _collect_emotions(
    bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]
) -> list[CharacterEmotionMetrics]:
    trajectories = reconstruct_emotion_trajectories(bundle, live_turns)

    results: list[CharacterEmotionMetrics] = []
    for character in bundle.characters:
        per_emotion: list[EmotionMetrics] = []
        for emotion, final_value in character.emotions.items():
            trajectory = trajectories.get((character.id, emotion))
            if trajectory is None:
                per_emotion.append(
                    EmotionMetrics(
                        emotion=emotion,
                        final=final_value,
                        min=None,
                        max=None,
                        max_consecutive_at_ceiling=None,
                    )
                )
                continue
            streak = best = 0
            for sample in trajectory[1:]:
                streak = streak + 1 if sample == 100 else 0
                best = max(best, streak)
            per_emotion.append(
                EmotionMetrics(
                    emotion=emotion,
                    final=final_value,
                    min=min(trajectory),
                    max=max(trajectory),
                    max_consecutive_at_ceiling=best,
                )
            )
        results.append(CharacterEmotionMetrics(character_id=character.id, emotions=per_emotion))
    return results


def _collect_pacing(live_turns: list[tuple[int, Path]]) -> PacingMetrics:
    stall_turns: set[int] = set()
    count = 0
    for turn, turn_dir in live_turns:
        applied, _ = read_state_diff(turn_dir)
        if not applied:
            continue
        for event in read_events(turn_dir):
            if event.get("type") == "pacing_stall":
                count += 1
                stall_turns.add(turn)
    return PacingMetrics(
        stall_event_count=count, max_consecutive_stall_turns=_longest_consecutive_run(stall_turns)
    )


def _collect_threads(
    bundle: WorldStateBundle,
    live_turns: list[tuple[int, Path]],
    last_turn_number: int | None,
) -> ThreadsMetrics:
    opened = advanced = resolved = 0
    for _, turn_dir in live_turns:
        applied, _ = read_state_diff(turn_dir)
        if not applied:
            continue
        for event in read_events(turn_dir):
            if event.get("type") != "thread_update":
                continue
            action = (event.get("effects") or {}).get("action")
            if action == "open":
                opened += 1
            elif action == "advance":
                advanced += 1
            elif action == "resolve":
                resolved += 1

    open_ages = [
        last_turn_number - thread.opened_turn
        for thread in bundle.unresolved_threads
        if thread.status != "resolved"
        and thread.opened_turn is not None
        and last_turn_number is not None
    ]
    return ThreadsMetrics(
        opened=opened,
        advanced=advanced,
        resolved=resolved,
        max_open_turns=max(open_ages) if open_ages else None,
    )


def _collect_threats(
    bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]
) -> list[ThreatMetrics]:
    # threat_id -> (turn, pressure-after-roll, roll_id, turn_dir) of its first threat_pressure event
    first_pressure: dict[str, tuple[int, int | None, str | None, Path]] = {}
    stage_turns: dict[str, dict[str, int]] = defaultdict(dict)

    for turn, turn_dir in live_turns:
        applied, _ = read_state_diff(turn_dir)
        if not applied:
            continue
        for event in read_events(turn_dir):
            effects = event.get("effects") or {}
            if event.get("type") == "threat_pressure":
                threat_id = effects.get("threat_id")
                if threat_id and threat_id not in first_pressure:
                    first_pressure[threat_id] = (
                        turn,
                        effects.get("pressure"),
                        effects.get("roll_id"),
                        turn_dir,
                    )
            elif event.get("type") == "threat_stage":
                threat_id = effects.get("threat_id")
                stage_at = effects.get("stage_at")
                if threat_id and stage_at is not None:
                    stage_turns[threat_id].setdefault(str(stage_at), turn)

    results: list[ThreatMetrics] = []
    for threat in bundle.world.threats:
        initial: int | None = None
        seen = first_pressure.get(threat.id)
        if seen is not None:
            _, pressure_after, roll_id, turn_dir = seen
            roll_result = _roll_result(turn_dir, roll_id)
            if pressure_after is not None and roll_result is not None:
                initial = max(0, pressure_after - roll_result)
        results.append(
            ThreatMetrics(
                threat_id=threat.id,
                initial_pressure=initial,
                final_pressure=threat.pressure,
                stage_fired_turns=dict(stage_turns.get(threat.id, {})),
            )
        )
    return results


def _collect_scenes(bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]) -> SceneMetrics:
    transitions = 0
    for _, turn_dir in live_turns:
        applied, changes = read_state_diff(turn_dir)
        if not applied:
            continue
        for change in changes:
            if (
                change.get("target") == "scene"
                and change.get("op") == "set"
                and change.get("path") == "status"
            ):
                transitions += 1

    active = [scene for scene in bundle.scenes if scene.status == SceneStatus.ACTIVE]
    return SceneMetrics(
        transition_count=transitions,
        final_active_count=len(active),
        final_active_scene_ids=[scene.id for scene in active],
        final_statuses={scene.id: scene.status.value for scene in bundle.scenes},
    )


def _collect_checks(live_turns: list[tuple[int, Path]]) -> ChecksMetrics:
    by_source: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    for _, turn_dir in live_turns:
        data = _load_yaml(turn_dir / "checks.yaml") or {}
        for finding in data.get("findings") or []:
            by_source[finding.get("source") or "unknown"] += 1
            by_severity[finding.get("severity") or "unknown"] += 1
    return ChecksMetrics(by_source=dict(by_source), by_severity=dict(by_severity))


def _collect_game(live_turns: list[tuple[int, Path]]) -> GameMetrics:
    combat_count = quest_opened = quest_advanced = quest_resolved = 0
    applied_pc_action_count = encounter_count = 0
    skill_check_successes = skill_check_total = 0
    for _, turn_dir in live_turns:
        applied, changes = read_state_diff(turn_dir)
        meta = _load_yaml(turn_dir / "meta.yaml") or {}
        review = _load_yaml(turn_dir / "review.yaml") or {}
        if not applied or meta.get("status") != "applied" or review.get("decision") == "reject_all":
            continue

        interventions = (_load_yaml(turn_dir / "intervention.yaml") or {}).get(
            "interventions"
        ) or []
        pc_directives = [
            item
            for item in interventions
            if item.get("type") == "character_directive"
            and item.get("user_role") == "player_character"
        ]
        candidates = _load_yaml(turn_dir / "agent_io" / "act_candidates.yaml") or []
        resolved_causes = {
            event.get("cause")
            for event in read_events(turn_dir)
            if not str(event.get("type") or "").endswith("_rejected")
        }
        resolved_pc_causes = {
            f"character:{candidate.get('character_id')}:{candidate.get('source_index')}"
            for candidate in candidates
            if any(
                candidate.get("character_id") == (directive.get("target") or {}).get("id")
                and candidate.get("action_text") == directive.get("content")
                for directive in pc_directives
            )
        }
        applied_pc_action_count += len(resolved_pc_causes & resolved_causes)

        rolls = {roll.get("id"): roll for roll in (_load_yaml(turn_dir / "rolls.yaml") or [])}
        for event in read_events(turn_dir):
            event_type = event.get("type")
            if event_type == "combat":
                combat_count += 1
            elif event_type == "encounter":
                encounter_count += 1
            elif event_type == "dice_roll_request":
                roll = rolls.get((event.get("effects") or {}).get("roll_id"))
                if roll is not None and roll.get("type") == "chance":
                    skill_check_total += 1
                    skill_check_successes += roll.get("outcome") == "success"

        for change in changes:
            if change.get("target") != "quests":
                continue
            if change.get("op") == "add" and change.get("path") == "":
                value = change.get("value") or {}
                if value.get("status") == "open":
                    quest_opened += 1
            elif change.get("op") == "set" and change.get("path") == "status":
                if change.get("value") == "advanced":
                    quest_advanced += 1
                elif change.get("value") == "resolved":
                    quest_resolved += 1

    success_rate = skill_check_successes / skill_check_total if skill_check_total else None
    return GameMetrics(
        combat_count=combat_count,
        quest_opened=quest_opened,
        quest_advanced=quest_advanced,
        quest_resolved=quest_resolved,
        applied_pc_action_count=applied_pc_action_count,
        encounter_count=encounter_count,
        skill_check_successes=skill_check_successes,
        skill_check_total=skill_check_total,
        skill_check_success_rate=success_rate,
    )
