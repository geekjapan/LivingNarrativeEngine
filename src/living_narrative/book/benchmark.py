"""Public, reproducible benchmark observations for long-form Book workflows."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.state.diff import fsync_directory
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore


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


def benchmark_book(workspace_root: Path, *, name: str) -> BookBenchmarkObservation:
    """Read one workspace without mutation and produce a path-free benchmark aggregate."""
    bundle = StateStore.load(workspace_root / "state")
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
    return BookBenchmarkObservation(
        name=name,
        planned_chapters=len(chapter_ids),
        accepted_chapters=accepted,
        revising_chapters=revising,
        blocked_chapters=blocked,
        attempt_count=attempt_count,
        open_thread_count=len(bundle.book_ledger.continuity.open_thread_ids),
        artifact_fingerprint=hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest(),
    )


def write_book_benchmark_report(
    path: Path, observations: Sequence[BookBenchmarkObservation]
) -> Path:
    """Atomically write a comparison-friendly public report with no workspace paths or prompts."""
    names = [observation.name for observation in observations]
    if len(names) != len(set(names)):
        raise ValueError("benchmark observation names must be unique")
    payload = {
        "schema_version": 1,
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
