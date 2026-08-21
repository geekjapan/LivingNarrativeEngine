"""Web adapter for durable chapter-production delivery.

HTTP callers only enqueue a reader-safe delivery job.  A separately started durable
worker invokes the domain runner, so an HTTP server restart never owns production state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from living_narrative.book.production_queue import (
    DurableProductionQueue,
    ProductionQueueJobNotFoundError,
    QueueJobState,
)
from living_narrative.book.production_runner import (
    ChapterProductionRunner,
    ChapterProductionRunStatus,
    ProductionRunPhase,
)
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project


class ChapterProductionRunAlreadyRunningError(Exception):
    """A Web caller requested a second queued or leased production delivery."""


class ChapterProductionRunNotFoundError(Exception):
    """No durable production delivery or prior runner artifact exists for this chapter."""


@dataclass(frozen=True)
class ProductionRunInfo:
    """Reader-safe projection of durable delivery state and runner status."""

    running: bool
    status: ChapterProductionRunStatus


def _initial_status(project_yaml: Path, chapter_id: str) -> ChapterProductionRunStatus:
    read = load_project(project_yaml)
    if not read.is_valid or read.paths is None:
        raise ValueError(f"invalid project: {project_yaml}")
    lifecycle = StateStore.load(read.paths.state).book_ledger.chapter(chapter_id).lifecycle
    return ChapterProductionRunStatus(
        run_id=f"chapter_{chapter_id}_pending",
        chapter_id=chapter_id,
        phase=ProductionRunPhase.CREATED,
        lifecycle=lifecycle,
    )


def _info_from_queue(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    queued = DurableProductionQueue().status(project_yaml, chapter_id)
    status = queued.status or _initial_status(project_yaml, chapter_id)
    return ProductionRunInfo(
        running=queued.state in {QueueJobState.QUEUED, QueueJobState.LEASED},
        status=status,
    )


def start_chapter_production_run(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    """Enqueue one chapter production delivery without running it in the Web process."""
    queue = DurableProductionQueue()
    try:
        existing = queue.status(project_yaml, chapter_id)
    except ProductionQueueJobNotFoundError:
        queued = queue.enqueue(project_yaml, chapter_id)
        return ProductionRunInfo(
            running=True,
            status=queued.status or _initial_status(project_yaml, chapter_id),
        )

    if existing.state in {QueueJobState.QUEUED, QueueJobState.LEASED}:
        raise ChapterProductionRunAlreadyRunningError(
            f"a chapter production run is already in progress for {chapter_id}"
        )
    if existing.state in {QueueJobState.FAILED, QueueJobState.STOPPED}:
        queued = queue.enqueue(project_yaml, chapter_id)
        return ProductionRunInfo(
            running=True,
            status=queued.status or _initial_status(project_yaml, chapter_id),
        )
    return _info_from_queue(project_yaml, chapter_id)


def get_chapter_production_run(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    """Read queue-backed public status, falling back to a pre-v0.6 runner artifact."""
    try:
        return _info_from_queue(project_yaml, chapter_id)
    except ProductionQueueJobNotFoundError:
        try:
            durable = ChapterProductionRunner().status(project_yaml, chapter_id)
        except ValueError as exc:
            raise ChapterProductionRunNotFoundError(chapter_id) from exc
        return ProductionRunInfo(running=False, status=durable)


def stop_chapter_production_run(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    """Stop an unclaimed job or record a phase-boundary stop for an active Runner."""
    queue = DurableProductionQueue()
    try:
        queued = queue.status(project_yaml, chapter_id)
    except ProductionQueueJobNotFoundError:
        queued = None
    if queued is not None and queued.state is QueueJobState.QUEUED:
        stopped = queue.stop(project_yaml, chapter_id)
        assert stopped.status is not None
        return ProductionRunInfo(running=False, status=stopped.status)
    if queued is not None and queued.state is QueueJobState.STOPPED:
        assert queued.status is not None
        return ProductionRunInfo(running=False, status=queued.status)
    try:
        status = ChapterProductionRunner().request_stop(project_yaml, chapter_id)
    except ValueError as exc:
        raise ChapterProductionRunNotFoundError(chapter_id) from exc
    return ProductionRunInfo(
        running=queued is not None and queued.state is QueueJobState.LEASED,
        status=status,
    )


__all__ = [
    "ChapterProductionRunAlreadyRunningError",
    "ChapterProductionRunNotFoundError",
    "ProductionRunInfo",
    "get_chapter_production_run",
    "start_chapter_production_run",
    "stop_chapter_production_run",
]
