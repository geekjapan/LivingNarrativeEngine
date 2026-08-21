"""In-process Web adapter for durable chapter Production Runner executions."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

from living_narrative.book.production_runner import (
    ChapterProductionRunner,
    ChapterProductionRunStatus,
    ProductionRunPhase,
)
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project


class ChapterProductionRunAlreadyRunningError(Exception):
    """A Web caller requested a second production run while one is still active."""


class ChapterProductionRunNotFoundError(Exception):
    """No durable or in-process production run exists for the requested chapter."""


@dataclass(frozen=True)
class ProductionRunInfo:
    """Reader-safe projection of durable status plus in-process execution state."""

    running: bool
    status: ChapterProductionRunStatus


@dataclass
class _RunState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    thread: threading.Thread | None = None
    running: bool = False
    status: ChapterProductionRunStatus | None = None


_RUN_STATES: dict[tuple[Path, str], _RunState] = {}
_REGISTRY_LOCK = threading.Lock()


def _state_for(project_yaml: Path, chapter_id: str) -> _RunState:
    key = (project_yaml.resolve(), chapter_id)
    with _REGISTRY_LOCK:
        return _RUN_STATES.setdefault(key, _RunState())


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


def start_chapter_production_run(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    """Start/resume a chapter runner in a daemon thread and return immediately.

    The thread is an execution convenience only. The runner's manifest is the recovery source of
    truth, and a later CLI/Web start can resume it after a server restart.
    """
    state = _state_for(project_yaml, chapter_id)
    with state.lock:
        if state.running:
            raise ChapterProductionRunAlreadyRunningError(
                f"a chapter production run is already in progress for {chapter_id}"
            )
        state.running = True
        state.status = _initial_status(project_yaml, chapter_id)

    def _worker() -> None:
        runner = ChapterProductionRunner()
        try:
            status = runner.run(project_yaml, chapter_id)
        except Exception:  # noqa: BLE001 - surface only a sanitized durable status
            try:
                status = runner.status(project_yaml, chapter_id)
            except ValueError:
                previous = state.status
                if previous is None:
                    previous = _initial_status(project_yaml, chapter_id)
                status = previous.model_copy(
                    update={
                        "phase": ProductionRunPhase.FAILED,
                        "failure_code": "production_run_failed",
                    }
                )
        with state.lock:
            state.status = status
            state.running = False

    thread = threading.Thread(target=_worker, daemon=True)
    with state.lock:
        state.thread = thread
        status = state.status
    thread.start()
    assert status is not None
    return ProductionRunInfo(running=True, status=status)


def get_chapter_production_run(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    """Read durable runner status, falling back to a just-started in-process projection."""
    state = _state_for(project_yaml, chapter_id)
    with state.lock:
        running = state.running
        in_process = state.status
    try:
        durable = ChapterProductionRunner().status(project_yaml, chapter_id)
    except ValueError as exc:
        if in_process is None:
            raise ChapterProductionRunNotFoundError(chapter_id) from exc
        return ProductionRunInfo(running=running, status=in_process)
    with state.lock:
        state.status = durable
    return ProductionRunInfo(running=running, status=durable)


def stop_chapter_production_run(project_yaml: Path, chapter_id: str) -> ProductionRunInfo:
    """Record a durable stop request; the Runner observes it at its next safe phase boundary."""
    state = _state_for(project_yaml, chapter_id)
    try:
        status = ChapterProductionRunner().request_stop(project_yaml, chapter_id)
    except ValueError as exc:
        raise ChapterProductionRunNotFoundError(chapter_id) from exc
    with state.lock:
        state.status = status
        running = state.running
    return ProductionRunInfo(running=running, status=status)


__all__ = [
    "ChapterProductionRunAlreadyRunningError",
    "ChapterProductionRunNotFoundError",
    "ProductionRunInfo",
    "get_chapter_production_run",
    "start_chapter_production_run",
    "stop_chapter_production_run",
]
