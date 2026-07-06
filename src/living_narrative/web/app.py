"""FastAPI app: a thin HTTP window over the existing engine (docs/issues/020, Track B).

No state mutation logic lives here — every route delegates to ``web.service`` (which in turn
delegates to ``workspace.loader``/``state.store``/``pipeline.driver``). YAML files remain the
single source of truth (spec-foundation.md D103); this module never holds state of its own
beyond the ``project_root`` it was created with.

Only imported from ``web.server`` and test modules that ``pytest.importorskip("fastapi")`` first
— never from ``living_narrative.cli`` at module scope, so the core test suite (and the CLI's
other commands) do not require the optional ``web`` extra to be installed.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse

from living_narrative.pipeline import LoadError, UnresolvedTurnError
from living_narrative.web.page import INDEX_HTML
from living_narrative.web.service import (
    ProjectNotFoundError,
    collect_narration,
    get_status,
    list_projects,
    resolve_project_dir,
    run_turn,
)


def create_app(project_root: Path) -> FastAPI:
    """Build the FastAPI app scoped to ``project_root`` (the directory ``serve`` was given).

    ``project_root`` is fixed at app-creation time (not a per-request parameter): every
    ``{name}`` path parameter below is resolved as a single path segment directly under it, so
    a client can only ever reach projects the operator chose to serve.
    """
    app = FastAPI(title="Living Narrative Engine — Web UI")

    def _project_yaml(name: str) -> Path:
        try:
            project_dir = resolve_project_dir(project_root, name)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return project_dir / "project.yaml"

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    @app.get("/api/projects")
    def api_list_projects() -> list[dict[str, str]]:
        return list_projects(project_root)

    @app.get("/api/project/{name}/status")
    def api_status(name: str) -> dict:
        project_yaml = _project_yaml(name)
        try:
            status = get_status(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return {
            "current_turn": status.current_turn,
            "pending_review": status.pending_review,
            "pending_review_turn": status.pending_review_turn,
            "scene": status.scene,
            "characters": status.characters,
        }

    @app.get("/api/project/{name}/narration", response_class=PlainTextResponse)
    def api_narration(name: str, from_turn: int = Query(1, alias="from", ge=1)) -> str:
        project_yaml = _project_yaml(name)
        try:
            return collect_narration(project_yaml, from_turn)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None

    @app.post("/api/project/{name}/turn")
    def api_run_turn(name: str) -> dict:
        project_yaml = _project_yaml(name)
        try:
            result = run_turn(project_yaml)
        except UnresolvedTurnError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LoadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "turn": result.turn,
            "status": result.status.value,
            "turn_dir": str(result.turn_dir),
        }

    return app
