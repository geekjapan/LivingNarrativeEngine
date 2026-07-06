"""Character arc / 伏線 (thread) report (docs/issues/028-029, Phase 6 "伏線・キャラクター変化
の一覧が出せる"). Pure read-only, no LLM calls — mirrors ``session/metrics.py``'s and
``export_replay/reconstruction.py``'s "load project, read turn artifacts + final state" shape.

Reuses (does not duplicate) ``session.metrics``'s turn-artifact readers
(``iter_live_turns``/``read_state_diff``/``read_events``) and its emotion-trajectory
reconstruction (``reconstruct_emotion_trajectories``) so the same ``applied``-turn gating and
baseline-replay semantics that module already established stay the single source of truth for
"what changed and when" — this module only turns that into change-point lists instead of a
min/max/final summary.

**Relationship value reconstruction limitation** (design decision, not present for emotions):
unlike ``CharacterState.emotions_baseline``, ``RelationshipState`` stores no separate
pre-turn-1 baseline field — ``bundle.relationships`` only ever holds the *current* (post-all-
turns) value. So the "resulting value" for a relationship delta can only be recovered by
working backward from that current value: candidate initial = final − Σ(deltas), then replay
forward with the same 0-100 clamp ``state.diff.apply_state_diff`` uses. If that replay's last
value doesn't reproduce the actual final value, an intermediate clamp must have fired at some
point and the true history is unrecoverable from the artifacts alone — every entry for that
(pair, dimension) is then reported with ``resulting_value=None`` rather than a guess. Only
``op: delta`` changes are considered (the only shape ``agents/state_manager.py`` ever emits
against ``target: relationship`` — grep-verified, mirrors ``metrics.py``'s equivalent note for
emotions); a manual ``set`` would silently be excluded from this report.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from living_narrative.session.metrics import (
    iter_live_turns,
    read_events,
    read_state_diff,
    reconstruct_emotion_trajectories,
)
from living_narrative.state.models import MemorySummary, WorldStateBundle
from living_narrative.state.store import StateLoadError, StateStore
from living_narrative.workspace.loader import load_project

_RELATIONSHIP_DIMENSIONS = frozenset({"trust", "affection", "tension", "suspicion"})


class ArcsError(RuntimeError):
    """The project at the given path could not be loaded (invalid config/state)."""


class EmotionChange(BaseModel):
    turn: int
    emotion: str
    before: int
    after: int


class CharacterEmotionArc(BaseModel):
    character_id: str
    changes: list[EmotionChange] = Field(default_factory=list)


class RelationshipChange(BaseModel):
    turn: int
    from_id: str
    to_id: str
    dimension: str
    delta: int
    resulting_value: int | None = None


class ThreadArc(BaseModel):
    id: str
    description: str
    opened_turn: int | None
    advances: int
    resolved_turn: int | None
    stalled_turns: int | None


class ArcsReport(BaseModel):
    emotions: list[CharacterEmotionArc] = Field(default_factory=list)
    relationships: list[RelationshipChange] = Field(default_factory=list)
    threads: list[ThreadArc] = Field(default_factory=list)
    memory_summaries: list[MemorySummary] = Field(default_factory=list)


def build_arcs_report(project_path: Path) -> ArcsReport:
    """Aggregate character-arc/伏線 data for the project at ``project_path`` (a
    ``project.yaml``).

    Raises ``ArcsError`` if the project config/required state files are missing or invalid
    (mirrors ``session.metrics.collect_metrics``'s error handling).
    """
    if not project_path.exists():
        raise ArcsError(f"project not found: {project_path}")

    result = load_project(project_path)
    if not result.is_valid:
        if result.errors:
            details = "; ".join(f"{issue.field}: {issue.message}" for issue in result.errors)
        else:
            details = f"missing state files: {', '.join(result.missing_state_files)}"
        raise ArcsError(f"invalid project at {project_path}: {details}")

    try:
        bundle = StateStore.load(result.paths.state)
    except StateLoadError as exc:
        details = "; ".join(f"{issue.file_path}: {issue.message}" for issue in exc.issues)
        raise ArcsError(f"invalid state at {result.paths.state}: {details}") from exc

    live_turns = iter_live_turns(result.paths.runs)
    last_turn_number = live_turns[-1][0] if live_turns else None

    return ArcsReport(
        emotions=_emotion_arcs(bundle, live_turns),
        relationships=_relationship_arcs(bundle, live_turns),
        threads=_thread_arcs(bundle, live_turns, last_turn_number),
        memory_summaries=sorted(bundle.memory_summaries, key=lambda summary: summary.up_to_turn),
    )


def render_arcs_markdown(report: ArcsReport) -> str:
    """Human-readable ``arcs.md`` (GM向け): emotion/relationship change points, thread table,
    memory summaries."""
    lines = ["# キャラクターアーク・伏線レポート (GM向け)", ""]

    lines.append("## 感情推移")
    if not report.emotions:
        lines.append("(キャラクターなし)")
    for character in report.emotions:
        lines.append(f"### {character.character_id}")
        if character.changes:
            lines.extend(
                f"- ターン{change.turn}: {change.emotion} {change.before}→{change.after}"
                for change in character.changes
            )
        else:
            lines.append("- (変化なし)")
    lines.append("")

    lines.append("## 関係推移")
    if report.relationships:
        for change in report.relationships:
            sign = "+" if change.delta >= 0 else ""
            resulting = (
                str(change.resulting_value) if change.resulting_value is not None else "不明"
            )
            lines.append(
                f"- ターン{change.turn}: {change.from_id}→{change.to_id} {change.dimension} "
                f"{sign}{change.delta} (結果値: {resulting})"
            )
    else:
        lines.append("(なし)")
    lines.append("")

    lines.append("## スレッド(伏線)")
    if report.threads:
        for thread in report.threads:
            lines.append(f"### {thread.id}: {thread.description}")
            opened = thread.opened_turn if thread.opened_turn is not None else "不明"
            lines.append(f"- 開始ターン: {opened}")
            lines.append(f"- 進展回数: {thread.advances}")
            if thread.resolved_turn is not None:
                lines.append(f"- 解決ターン: {thread.resolved_turn}")
            elif thread.stalled_turns is not None:
                lines.append(f"- 放置ターン数: {thread.stalled_turns}")
            else:
                lines.append("- 状態: 未解決 (放置ターン数不明)")
    else:
        lines.append("(なし)")
    lines.append("")

    lines.append("## メモリ要約")
    if report.memory_summaries:
        lines.extend(
            f"- (ターン{summary.up_to_turn}まで) {summary.text}"
            for summary in report.memory_summaries
        )
    else:
        lines.append("(なし)")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


# --- section collectors ------------------------------------------------------


def _emotion_arcs(
    bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]
) -> list[CharacterEmotionArc]:
    trajectories = reconstruct_emotion_trajectories(bundle, live_turns)

    results: list[CharacterEmotionArc] = []
    for character in bundle.characters:
        changes: list[EmotionChange] = []
        for emotion in character.emotions:
            trajectory = trajectories.get((character.id, emotion))
            if trajectory is None:
                continue
            for index in range(1, len(trajectory)):
                before, after = trajectory[index - 1], trajectory[index]
                if before == after:
                    continue
                turn = live_turns[index - 1][0]
                changes.append(
                    EmotionChange(turn=turn, emotion=emotion, before=before, after=after)
                )
        changes.sort(key=lambda change: (change.turn, change.emotion))
        results.append(CharacterEmotionArc(character_id=character.id, changes=changes))
    return results


def _reconstruct_relationship_values(
    deltas: list[int], final_value: int | None
) -> list[int | None]:
    """Per-delta resulting value, or ``None`` for every entry when it isn't reliably
    computable — see this module's docstring for why."""
    if final_value is None:
        return [None] * len(deltas)
    value = final_value - sum(deltas)
    trajectory: list[int] = []
    for delta in deltas:
        value = max(0, min(100, value + delta))
        trajectory.append(value)
    if trajectory[-1] != final_value:
        return [None] * len(deltas)
    return trajectory


def _relationship_arcs(
    bundle: WorldStateBundle, live_turns: list[tuple[int, Path]]
) -> list[RelationshipChange]:
    # (from_id, to_id, dimension) -> [(turn, delta), ...] in turn order
    raw: dict[tuple[str, str, str], list[tuple[int, int]]] = defaultdict(list)
    for turn, turn_dir in live_turns:
        applied, changes = read_state_diff(turn_dir)
        if not applied:
            continue
        for change in changes:
            if change.get("target") != "relationship" or change.get("op") != "delta":
                continue
            dimension = change.get("path")
            if dimension not in _RELATIONSHIP_DIMENSIONS:
                continue
            key = change.get("id") or ""
            from_id, sep, to_id = key.partition("__")
            if not sep:
                continue
            raw[(from_id, to_id, dimension)].append((turn, int(change.get("value") or 0)))

    relationships_by_key = {(r.from_, r.to): r for r in bundle.relationships}

    results: list[RelationshipChange] = []
    for (from_id, to_id, dimension), entries in raw.items():
        relationship = relationships_by_key.get((from_id, to_id))
        final_value = getattr(relationship, dimension, None) if relationship else None
        resulting_values = _reconstruct_relationship_values(
            [delta for _, delta in entries], final_value
        )
        for (turn, delta), resulting in zip(entries, resulting_values):
            results.append(
                RelationshipChange(
                    turn=turn,
                    from_id=from_id,
                    to_id=to_id,
                    dimension=dimension,
                    delta=delta,
                    resulting_value=resulting,
                )
            )

    results.sort(key=lambda change: (change.turn, change.from_id, change.to_id, change.dimension))
    return results


def _thread_arcs(
    bundle: WorldStateBundle,
    live_turns: list[tuple[int, Path]],
    last_turn_number: int | None,
) -> list[ThreadArc]:
    advances: Counter[str] = Counter()
    resolved_turn: dict[str, int] = {}
    for turn, turn_dir in live_turns:
        applied, _ = read_state_diff(turn_dir)
        if not applied:
            continue
        for event in read_events(turn_dir):
            if event.get("type") != "thread_update":
                continue
            effects: dict[str, Any] = event.get("effects") or {}
            thread_id = effects.get("thread_id")
            if not thread_id:
                continue
            action = effects.get("action")
            if action == "advance":
                advances[thread_id] += 1
            elif action == "resolve":
                resolved_turn.setdefault(thread_id, turn)

    results: list[ThreadArc] = []
    for thread in bundle.unresolved_threads:
        resolved_at = resolved_turn.get(thread.id)
        stalled: int | None = None
        if resolved_at is None and thread.status != "resolved":
            if thread.opened_turn is not None and last_turn_number is not None:
                # Mirrors session.metrics.ThreadsMetrics.max_open_turns' definition (last_turn -
                # opened_turn), per-thread instead of only the max across all open threads.
                stalled = last_turn_number - thread.opened_turn
        results.append(
            ThreadArc(
                id=thread.id,
                description=thread.description,
                opened_turn=thread.opened_turn,
                advances=advances.get(thread.id, 0),
                resolved_turn=resolved_at,
                stalled_turns=stalled,
            )
        )
    return results
