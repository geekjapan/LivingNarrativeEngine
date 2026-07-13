"""Background auto-run coordination for the web layer."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

from living_narrative.pipeline import TurnPipeline, TurnStatus
from living_narrative.state.transaction import project_lock


class AutoRunAlreadyRunningError(Exception):
    """An ``auto`` run was requested for a project that already has one in progress."""


@dataclass
class _ProjectRunState:
    """Mutable in-process auto-run state for one project directory, guarded by ``lock``."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    stop_flag: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    running: bool = False
    current_turn: int = 0
    last_status: str | None = None
    stopped_reason: str | None = None


_RUN_STATES: dict[Path, _ProjectRunState] = {}
_REGISTRY_LOCK = threading.Lock()


def _run_state_for(project_dir: Path) -> _ProjectRunState:
    with _REGISTRY_LOCK:
        return _RUN_STATES.setdefault(project_dir, _ProjectRunState())


@dataclass(frozen=True)
class RunStatus:
    running: bool
    current_turn: int
    last_status: str | None
    stopped_reason: str | None


def get_run_status(project_yaml: Path) -> RunStatus:
    state = _run_state_for(project_yaml.parent)
    with state.lock:
        return RunStatus(
            running=state.running,
            current_turn=state.current_turn,
            last_status=state.last_status,
            stopped_reason=state.stopped_reason,
        )


def request_stop(project_yaml: Path) -> None:
    """Ask a running ``auto`` loop to stop at the next turn boundary."""
    _run_state_for(project_yaml.parent).stop_flag.set()


def start_auto_run(project_yaml: Path, turns: int) -> None:
    """Run up to ``turns`` turns in a background thread, one locked turn at a time."""
    state = _run_state_for(project_yaml.parent)
    with state.lock:
        if state.running:
            raise AutoRunAlreadyRunningError(
                f"an auto run is already in progress for {project_yaml}"
            )
        state.running = True
        state.stopped_reason = None
        state.last_status = None
        state.stop_flag.clear()

    def _worker() -> None:
        pipeline = TurnPipeline()
        stopped_reason: str | None = "turns_complete"
        try:
            for _ in range(turns):
                if state.stop_flag.is_set():
                    stopped_reason = "stopped"
                    break
                with project_lock(project_yaml.parent):
                    result = pipeline.run(project_yaml, _lock_held=True)
                with state.lock:
                    state.current_turn = result.turn
                    state.last_status = result.status.value
                if result.status != TurnStatus.APPLIED:
                    stopped_reason = result.status.value
                    break
            else:
                stopped_reason = "turns_complete"
        except Exception as exc:  # noqa: BLE001 - must surface via run_status, never swallow
            with state.lock:
                state.last_status = "failed"
            stopped_reason = f"error: {exc}"
        finally:
            with state.lock:
                state.running = False
                state.stopped_reason = stopped_reason

    thread = threading.Thread(target=_worker, daemon=True)
    with state.lock:
        state.thread = thread
    thread.start()


__all__ = [
    "AutoRunAlreadyRunningError",
    "RunStatus",
    "get_run_status",
    "request_stop",
    "start_auto_run",
]
