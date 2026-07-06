"""Project resolution, status, and narration helpers for the web layer (docs/issues/020, 021-022).

Deliberately FastAPI-free: this module only calls into the existing engine (``workspace.loader``,
``state.store``, ``pipeline.driver``, ``session.review``) and shapes plain dicts/dataclasses.
Keeping it import-light means it can be unit tested even in environments without the optional
``web`` extra installed — only ``web.app``/``web.server`` need FastAPI/uvicorn.
"""

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from living_narrative.cli._common import read_narration_body
from living_narrative.intervention.history import load_history
from living_narrative.pipeline import TurnPipeline, TurnRunResult, TurnStatus
from living_narrative.pipeline.turn_numbering import read_turn_status, turn_dir_path
from living_narrative.session.mode import MODE_PERMISSIONS
from living_narrative.session.resume import restore_resume_state
from living_narrative.session.review import ReviewDecision, ReviewResult, resolve_review
from living_narrative.state.models import SceneStatus, UserMode
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project

__all__ = [
    "AutoRunAlreadyRunningError",
    "InterventionsInfo",
    "NoPendingReviewError",
    "PermissionsInfo",
    "ProjectNotFoundError",
    "RunStatus",
    "TurnNarration",
    "collect_narration",
    "collect_structured_narration",
    "get_interventions",
    "get_permissions",
    "get_run_status",
    "get_status",
    "list_projects",
    "request_stop",
    "resolve_project_dir",
    "run_turn",
    "start_auto_run",
    "submit_review",
]

_LIVE_TURN_DIR_RE = re.compile(r"^turn_(\d+)$")


class ProjectNotFoundError(Exception):
    """A project name did not resolve to a valid project directly under the served root."""


class AutoRunAlreadyRunningError(Exception):
    """An ``auto`` run was requested for a project that already has one in progress."""


class NoPendingReviewError(Exception):
    """A review decision was submitted but no turn is pending review for this project."""


def resolve_project_dir(root: Path, name: str) -> Path:
    """Resolve ``name`` (a single path segment) to a project directory directly under ``root``.

    Rejects path traversal: empty names, embedded separators, ``.``/``..``, and anything that
    does not resolve (after following symlinks) to a direct child of ``root`` containing a
    ``project.yaml``.
    """
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise ProjectNotFoundError(name)
    root_resolved = root.resolve()
    candidate = (root / name).resolve()
    if candidate.parent != root_resolved:
        raise ProjectNotFoundError(name)
    if not (candidate / "project.yaml").is_file():
        raise ProjectNotFoundError(name)
    return candidate


def list_projects(root: Path) -> list[dict[str, str]]:
    """Scan ``root``'s immediate subdirectories for ``project.yaml`` files."""
    if not root.is_dir():
        return []
    projects: list[dict[str, str]] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        project_yaml = entry / "project.yaml"
        if not entry.is_dir() or not project_yaml.is_file():
            continue
        read = load_project(project_yaml)
        title = read.config.title if read.config is not None else entry.name
        projects.append({"name": entry.name, "title": title})
    return projects


@dataclass(frozen=True)
class ProjectStatus:
    current_turn: int
    pending_review: bool
    pending_review_turn: int | None
    scene: dict | None
    characters: list[dict]


def get_status(project_yaml: Path) -> ProjectStatus:
    """Status summary: turn count, active scene, character names/status.

    Deliberately excludes ``private_mind``/``secrets``/``knowledge`` and anything under
    ``gm_vault`` — mirrors ``cli/status.py``'s no-leak contract (see ``spec-foundation.md``
    §4 information-scope model).
    """
    read = load_project(project_yaml)
    if not read.is_valid:
        raise ProjectNotFoundError(str(project_yaml))

    bundle = StateStore.load(read.paths.state)
    resume_state = restore_resume_state(read.paths.runs, read.paths.root / "interventions.yaml")
    active_scene = next((s for s in bundle.scenes if s.status == SceneStatus.ACTIVE), None)

    return ProjectStatus(
        current_turn=resume_state.last_applied_turn or 0,
        pending_review=resume_state.pending_review_turn is not None,
        pending_review_turn=resume_state.pending_review_turn,
        scene=(
            {"id": active_scene.id, "location": active_scene.location, "mood": active_scene.mood}
            if active_scene is not None
            else None
        ),
        characters=[
            {"id": c.id, "name": c.name, "status": c.status.value} for c in bundle.characters
        ],
    )


def collect_narration(project_yaml: Path, from_turn: int) -> str:
    """Concatenate ``narration.md`` bodies for consecutive turns starting at ``from_turn``.

    ``narration.md`` is written with ``visibility: reader`` in its frontmatter unconditionally
    (``pipeline/writer.py::write_narration``) — it is the reader-facing view by construction, so
    no further visibility filtering is needed here. Stops at the first missing turn directory.
    """
    read = load_project(project_yaml)
    if not read.is_valid:
        raise ProjectNotFoundError(str(project_yaml))

    bodies: list[str] = []
    turn = max(from_turn, 1)
    while True:
        turn_dir = turn_dir_path(read.paths.runs, turn)
        if not turn_dir.exists():
            break
        body = read_narration_body(turn_dir / "narration.md")
        if body:
            bodies.append(body)
        turn += 1
    return "\n\n".join(bodies)


def run_turn(
    project_yaml: Path,
    *,
    intervention_text: str | None = None,
    intervention_drafts: list[dict[str, Any]] | None = None,
) -> TurnRunResult:
    """Run one turn synchronously (blocking). Multi-turn background runs use ``start_auto_run``.

    ``intervention_text``/``intervention_drafts`` are passed through verbatim to
    ``TurnPipeline.run`` (docs/issues/023) — same free-text/direct-input contract the CLI's
    ``turn --intervention``/``--type`` flags use (``cli/turn.py``), just sourced from an HTTP
    body instead of argv.

    May raise ``pipeline.LoadError``/``pipeline.UnresolvedTurnError``, same as the CLI's
    ``turn`` command; callers translate those to HTTP errors (see ``web.app``).
    """
    return TurnPipeline().run(
        project_yaml,
        intervention_text=intervention_text,
        intervention_drafts=intervention_drafts,
    )


@dataclass(frozen=True)
class TurnNarration:
    turn: int
    status: str | None
    text: str


def collect_structured_narration(project_yaml: Path, from_turn: int) -> list[TurnNarration]:
    """Per-turn ``narration.md`` bodies with each turn's ``meta.yaml`` status (docs/issues/021-022).

    Same reader-visible-only contract as ``collect_narration`` (``narration.md`` is always
    written with ``visibility: reader``); this just adds turn number/status framing so the UI
    can render per-turn blocks with status badges instead of one flat blob of text.
    """
    read = load_project(project_yaml)
    if not read.is_valid:
        raise ProjectNotFoundError(str(project_yaml))

    entries: list[TurnNarration] = []
    turn = max(from_turn, 1)
    while True:
        turn_dir = turn_dir_path(read.paths.runs, turn)
        if not turn_dir.exists():
            break
        status = read_turn_status(turn_dir)
        body = read_narration_body(turn_dir / "narration.md") or ""
        entries.append(TurnNarration(turn=turn, status=status.value if status else None, text=body))
        turn += 1
    return entries


def submit_review(project_yaml: Path, decision: ReviewDecision | str) -> ReviewResult:
    """Resolve the pending-review turn via the existing ``session.review.resolve_review``.

    Only ``accept_all``/``reject_all`` are exposed over the API for now (021-022 scope) — the
    richer ``partial``/``edit``/``rerun_turn`` decisions stay CLI-only until a future issue adds
    a diff-review UI (issue 025 in ``docs/plan/feature-dag.md``).
    """
    read = load_project(project_yaml)
    if not read.is_valid:
        raise ProjectNotFoundError(str(project_yaml))

    resume_state = restore_resume_state(read.paths.runs, read.paths.root / "interventions.yaml")
    pending_turn = resume_state.pending_review_turn
    if pending_turn is None:
        raise NoPendingReviewError(f"no turn is pending review for {project_yaml}")

    turn_dir = turn_dir_path(read.paths.runs, pending_turn)
    return resolve_review(
        workspace_root=read.paths.root,
        state_dir=read.paths.state,
        turn_dir=turn_dir,
        decision=decision,
        decided_by=read.config.user_mode,
    )


@dataclass(frozen=True)
class PermissionsInfo:
    user_mode: str
    allowed_types: list[str]


def get_permissions(project_yaml: Path) -> PermissionsInfo:
    """The project's ``user_mode`` and the intervention types it may submit (docs/issues/023).

    Source of truth is ``session.mode.MODE_PERMISSIONS`` (D114: session-autonomy owns the
    permission matrix) — this is a read-only projection of it, not a second copy.
    """
    read = load_project(project_yaml)
    if not read.is_valid:
        raise ProjectNotFoundError(str(project_yaml))

    mode = UserMode(read.config.user_mode)
    allowed = sorted(t.value for t in MODE_PERMISSIONS[mode].allowed_interventions)
    return PermissionsInfo(user_mode=mode.value, allowed_types=allowed)


def _latest_live_turn_number(runs_dir: Path) -> int | None:
    """Highest ``turn_NNNN`` (never a ``_discarded_n`` variant) directory number, if any."""
    if not runs_dir.exists():
        return None
    numbers = [
        int(match.group(1))
        for entry in runs_dir.iterdir()
        if entry.is_dir() and (match := _LIVE_TURN_DIR_RE.match(entry.name))
    ]
    return max(numbers) if numbers else None


@dataclass(frozen=True)
class InterventionsInfo:
    history: list[dict[str, Any]]
    last_turn: dict[str, Any] | None


def get_interventions(project_yaml: Path) -> InterventionsInfo:
    """Project-wide intervention history index + the most recent turn's accepted/rejected
    interventions (docs/issues/023).

    ``history`` mirrors ``workspace/interventions.yaml`` (``intervention.history.load_history``);
    ``last_turn`` reads that same turn's ``intervention.yaml`` directly (artifacts are written
    even on a failed turn — spec-foundation.md §6 — so this can't reuse the "last *applied*
    turn" resume bookkeeping, which only tracks applied turns).
    """
    read = load_project(project_yaml)
    if not read.is_valid:
        raise ProjectNotFoundError(str(project_yaml))

    history = load_history(read.paths.root / "interventions.yaml")
    history_dicts = [entry.model_dump(mode="json") for entry in history.entries]

    last_turn: dict[str, Any] | None = None
    last_turn_number = _latest_live_turn_number(read.paths.runs)
    if last_turn_number is not None:
        intervention_path = turn_dir_path(read.paths.runs, last_turn_number) / "intervention.yaml"
        if intervention_path.exists():
            data = yaml.safe_load(intervention_path.read_text(encoding="utf-8")) or {}
            last_turn = {
                "turn": last_turn_number,
                "interventions": data.get("interventions", []),
                "rejections": data.get("rejections", []),
            }

    return InterventionsInfo(history=history_dicts, last_turn=last_turn)


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
    """Ask a running ``auto`` loop to stop at the next turn boundary. A no-op if none is running."""
    state = _run_state_for(project_yaml.parent)
    state.stop_flag.set()


def start_auto_run(project_yaml: Path, turns: int) -> None:
    """Start a background thread running up to ``turns`` turns via the normal ``TurnPipeline``.

    Raises ``AutoRunAlreadyRunningError`` if a run for this project is already in progress
    (mirrors the "one active run per project" constraint the CLI's ``auto`` command gets for
    free by being a single blocking process). The loop checks the stop flag at each turn
    boundary (before starting the next turn) and halts on any non-``applied`` status, same as
    ``session.loop.run_auto_loop``.
    """
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
                result = pipeline.run(project_yaml)
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
