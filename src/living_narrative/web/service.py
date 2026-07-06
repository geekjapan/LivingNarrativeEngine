"""Project resolution, status, and narration helpers for the web layer (docs/issues/020).

Deliberately FastAPI-free: this module only calls into the existing engine (``workspace.loader``,
``state.store``, ``pipeline.driver``) and shapes plain dicts/dataclasses. Keeping it import-light
means it can be unit tested even in environments without the optional ``web`` extra installed —
only ``web.app``/``web.server`` need FastAPI/uvicorn.
"""

from dataclasses import dataclass
from pathlib import Path

from living_narrative.cli._common import read_narration_body
from living_narrative.pipeline import TurnPipeline, TurnRunResult
from living_narrative.pipeline.turn_numbering import turn_dir_path
from living_narrative.session.resume import restore_resume_state
from living_narrative.state.models import SceneStatus
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project

__all__ = [
    "ProjectNotFoundError",
    "collect_narration",
    "get_status",
    "list_projects",
    "resolve_project_dir",
    "run_turn",
]


class ProjectNotFoundError(Exception):
    """A project name did not resolve to a valid project directly under the served root."""


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


def run_turn(project_yaml: Path) -> TurnRunResult:
    """Run one turn synchronously (blocking — async execution is deferred to issue 022).

    May raise ``pipeline.LoadError``/``pipeline.UnresolvedTurnError``, same as the CLI's
    ``turn`` command; callers translate those to HTTP errors (see ``web.app``).
    """
    return TurnPipeline().run(project_yaml)
