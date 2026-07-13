"""Atomic artifact writers for ``workspace/runs/turn_NNNN/`` (spec-foundation.md §6)."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from living_narrative.llm.metadata import CallMetadata, build_turn_meta
from living_narrative.pipeline.models import (
    ActRecord,
    CheckResult,
    ErrorReport,
    InterventionFile,
    RejectedChange,
)
from living_narrative.pipeline.status import TurnStatus
from living_narrative.pipeline.version import PIPELINE_VERSION
from living_narrative.random.engine import append_roll
from living_narrative.random.models import Roll
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            stream.write(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_intervention(turn_dir: Path, intervention: InterventionFile) -> None:
    _atomic_write_yaml(turn_dir / "intervention.yaml", intervention.model_dump(mode="json"))


def write_agent_io(turn_dir: Path, records: list[ActRecord]) -> None:
    agent_io_dir = turn_dir / "agent_io"
    agent_io_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_yaml(
        agent_io_dir / "act.yaml", [record.model_dump(mode="json") for record in records]
    )


def write_agent_io_component(turn_dir: Path, name: str, data: Any) -> None:
    _atomic_write_yaml(turn_dir / "agent_io" / f"{name}.yaml", data)


def write_events(turn_dir: Path, events: list[Event]) -> None:
    _atomic_write_yaml(
        turn_dir / "events.yaml", [event.model_dump(mode="json") for event in events]
    )


def ensure_rolls_file(turn_dir: Path) -> Path:
    path = turn_dir / "rolls.yaml"
    if not path.exists():
        _atomic_write_yaml(path, [])
    return path


def make_roll_recorder(turn_dir: Path) -> Callable[[Roll], None]:
    rolls_path = ensure_rolls_file(turn_dir)

    def record(roll: Roll) -> None:
        append_roll(rolls_path, roll)

    return record


def write_checks(turn_dir: Path, results: list[CheckResult]) -> None:
    _atomic_write_yaml(
        turn_dir / "checks.yaml",
        {"findings": [result.model_dump(mode="json") for result in results]},
    )


def write_state_diff(
    turn_dir: Path,
    diff: StateDiff,
    rejected_changes: list[RejectedChange],
    applied: bool,
) -> None:
    _atomic_write_yaml(
        turn_dir / "state_diff.yaml",
        {
            "diff": diff.model_dump(mode="json"),
            "rejected_changes": [item.model_dump(mode="json") for item in rejected_changes],
            "applied": applied,
        },
    )


def write_narration(turn_dir: Path, turn: int, style: str, text: str) -> None:
    frontmatter = yaml.safe_dump(
        {"turn": turn, "style": style, "visibility": "reader"},
        allow_unicode=True,
        sort_keys=False,
    )
    _atomic_write_text(turn_dir / "narration.md", f"---\n{frontmatter}---\n\n{text}\n")


def build_meta_dict(
    *,
    turn: int,
    status: TurnStatus,
    commit_mode: str,
    phase_durations: dict[str, float],
    calls: list[CallMetadata],
    rng_draws_consumed: int,
    rng_start_offset: int | None = None,
    diff_id: str | None = None,
    state_hash_before: str | None = None,
    state_hash_after: str | None = None,
    error: ErrorReport | None = None,
) -> dict[str, Any]:
    turn_meta = build_turn_meta(calls)
    meta: dict[str, Any] = {
        "turn": turn,
        "status": status.value,
        "commit_mode": commit_mode,
        "phase_durations": phase_durations,
        "llm_call_count": len(calls),
        "llm_calls": turn_meta["llm_calls"],
        "prompt_hashes": [call.prompt_hash for call in calls],
        "rng_draws_consumed": rng_draws_consumed,
        "pipeline_version": PIPELINE_VERSION,
    }
    if rng_start_offset is not None:
        meta["rng_start_offset"] = rng_start_offset
    if diff_id is not None:
        meta["diff_id"] = diff_id
    if state_hash_before is not None:
        meta["state_hash_before"] = state_hash_before
    if state_hash_after is not None:
        meta["state_hash_after"] = state_hash_after
    if turn_meta["llm_tokens_total"] is not None:
        meta["llm_tokens_total"] = turn_meta["llm_tokens_total"]
    if error is not None:
        meta["error"] = error.model_dump(mode="json")
    return meta


def write_meta(turn_dir: Path, meta: dict[str, Any]) -> None:
    _atomic_write_yaml(turn_dir / "meta.yaml", meta)
