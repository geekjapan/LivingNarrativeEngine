"""Public, reproducible benchmark observations for long-form Book workflows."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from living_narrative.book.coordinator import resolve_workspace_dirs
from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.state.diff import fsync_directory
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import WorkspacePaths


class BookBenchmarkSLO(BaseModel):
    """Explicit, reader-safe maximum duration for one benchmark observation."""

    max_duration_ms: int = Field(ge=0)


class BookBenchmarkSLOEvaluation(BaseModel):
    """Reader-safe outcome of applying one benchmark duration budget."""

    within_budget: bool
    duration_ms: int = Field(ge=0)
    max_duration_ms: int = Field(ge=0)
    reason: str | None = None


class BookBenchmarkObservation(BaseModel):
    """Safe aggregate measurements for one BookPlan benchmark fixture."""

    name: str = Field(min_length=1)
    planned_chapters: int = Field(ge=0)
    accepted_chapters: int = Field(ge=0)
    revising_chapters: int = Field(ge=0)
    blocked_chapters: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    open_thread_count: int = Field(ge=0)
    artifact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_run_count: int = Field(default=0, ge=0)
    resumed_production_run_count: int = Field(default=0, ge=0)
    stopped_production_run_count: int = Field(default=0, ge=0)
    failed_production_run_count: int = Field(default=0, ge=0)
    production_run_event_count: int = Field(default=0, ge=0)
    production_run_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_ms: int = Field(default=0, ge=0)


def evaluate_book_benchmark_slo(
    observation: BookBenchmarkObservation,
    slo: BookBenchmarkSLO,
) -> BookBenchmarkSLOEvaluation:
    """Evaluate an explicit benchmark duration SLO without mutating any artifact."""
    within_budget = observation.duration_ms <= slo.max_duration_ms
    return BookBenchmarkSLOEvaluation(
        within_budget=within_budget,
        duration_ms=observation.duration_ms,
        max_duration_ms=slo.max_duration_ms,
        reason=None if within_budget else "benchmark duration exceeded",
    )


def _read_public_run_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping production run artifact: {path.name}")
    return payload


def _production_run_observations(runs_dir: Path) -> tuple[dict[str, int], str]:
    """Summarize durable run progress without exposing paths, prompts, bodies, or failure detail."""
    root = runs_dir / "chapter_production"
    counts = {
        "production_run_count": 0,
        "resumed_production_run_count": 0,
        "stopped_production_run_count": 0,
        "failed_production_run_count": 0,
        "production_run_event_count": 0,
    }
    records: list[dict[str, object]] = []
    if not root.is_dir():
        fingerprint_input = json.dumps(records, sort_keys=True, separators=(",", ":"))
        return counts, hashlib.sha256(fingerprint_input.encode()).hexdigest()

    for manifest_path in sorted(root.glob("*/*/manifest.yaml")):
        manifest = _read_public_run_mapping(manifest_path)
        phase = str(manifest.get("phase", "unknown"))
        events_dir = manifest_path.parent / "events"
        event_paths = sorted(events_dir.glob("*.yaml")) if events_dir.is_dir() else []
        events = [_read_public_run_mapping(path) for path in event_paths]
        links_path = manifest_path.parent / "links.yaml"
        failure_path = manifest_path.parent / "failure.yaml"
        links = _read_public_run_mapping(links_path) if links_path.is_file() else {}
        failure = _read_public_run_mapping(failure_path) if failure_path.is_file() else {}
        counts["production_run_count"] += 1
        counts["production_run_event_count"] += len(events)
        counts["resumed_production_run_count"] += any(
            event.get("resumed_without_provider") is True for event in events
        )
        counts["stopped_production_run_count"] += phase == "stopped"
        counts["failed_production_run_count"] += phase == "failed"
        records.append(
            {
                "chapter_id": manifest.get("chapter_id"),
                "run_id": manifest.get("run_id"),
                "phase": phase,
                "event_count": len(events),
                "resumed_without_provider": any(
                    event.get("resumed_without_provider") is True for event in events
                ),
                "candidate_sha256": links.get("candidate_sha256"),
                "failure_code": failure.get("code") if phase == "failed" else None,
            }
        )
    fingerprint_input = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return counts, hashlib.sha256(fingerprint_input.encode()).hexdigest()


def benchmark_book(workspace: Path | WorkspacePaths, *, name: str) -> BookBenchmarkObservation:
    """Read one workspace without mutation and produce a path-free benchmark aggregate.

    Accepts the resolved ``load_project()`` paths so a configured ``workspace.state`` is measured
    instead of the default layout.
    """
    started_at_ns = time.perf_counter_ns()
    workspace_root, state_dir, runs_dir = resolve_workspace_dirs(workspace)
    bundle = StateStore.load(state_dir)
    chapter_ids = [chapter.id for chapter in bundle.book_plan.chapters]
    accepted = 0
    revising = 0
    blocked = 0
    attempt_count = 0
    lineage_records: list[dict[str, object]] = []
    for chapter_id in chapter_ids:
        lifecycle = bundle.book_ledger.chapter(chapter_id).lifecycle
        accepted += lifecycle is ChapterLifecycle.ACCEPTED
        revising += lifecycle is ChapterLifecycle.REVISING
        blocked += lifecycle in {ChapterLifecycle.REVIEW, ChapterLifecycle.REVISING}
        lineage = load_chapter_lineage(workspace_root / "books" / "chapters", chapter_id)
        attempt_count += len(lineage.attempts)
        lineage_records.append(
            {
                "chapter_id": chapter_id,
                "accepted_attempt_id": lineage.accepted_attempt_id,
                "attempts": [
                    {"id": attempt.id, "candidate_sha256": attempt.candidate_sha256}
                    for attempt in lineage.attempts
                ],
            }
        )
    fingerprint_input = json.dumps(
        {"chapters": lineage_records},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    artifact_fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()
    run_counts, production_run_fingerprint = _production_run_observations(runs_dir)
    benchmark_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "artifact_fingerprint": artifact_fingerprint,
                "production_run_fingerprint": production_run_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return BookBenchmarkObservation(
        name=name,
        planned_chapters=len(chapter_ids),
        accepted_chapters=accepted,
        revising_chapters=revising,
        blocked_chapters=blocked,
        attempt_count=attempt_count,
        open_thread_count=len(bundle.book_ledger.continuity.open_thread_ids),
        artifact_fingerprint=artifact_fingerprint,
        production_run_fingerprint=production_run_fingerprint,
        benchmark_fingerprint=benchmark_fingerprint,
        duration_ms=(time.perf_counter_ns() - started_at_ns) // 1_000_000,
        **run_counts,
    )


def write_book_benchmark_report(
    path: Path, observations: Sequence[BookBenchmarkObservation]
) -> Path:
    """Atomically write a comparison-friendly public report with no workspace paths or prompts."""
    names = [observation.name for observation in observations]
    if len(names) != len(set(names)):
        raise ValueError("benchmark observation names must be unique")
    payload = {
        "schema_version": 3,
        "books": [item.model_dump(mode="json") for item in observations],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return path
