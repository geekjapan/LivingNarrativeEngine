"""FastAPI app: a thin HTTP window over the existing engine (docs/issues/020, 021-022, Track B).

No state mutation logic lives here — every route delegates to ``web.service`` (which in turn
delegates to ``workspace.loader``/``state.store``/``pipeline.driver``/``session.review``). YAML
files remain the single source of truth (spec-foundation.md D103); this module never holds state
of its own beyond the ``project_root`` it was created with (the auto-run registry lives in
``web.service``, keyed by resolved project directory).

Only imported from ``web.server`` and test modules that ``pytest.importorskip("fastapi")`` first
— never from ``living_narrative.cli`` at module scope, so the core test suite (and the CLI's
other commands) do not require the optional ``web`` extra to be installed.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from living_narrative.pipeline import LoadError, UnresolvedTurnError
from living_narrative.session.review import ReviewDecision, ReviewStateError
from living_narrative.web.page import INDEX_HTML
from living_narrative.web.service import (
    AutoRunAlreadyRunningError,
    NoPendingReviewError,
    ProjectNotFoundError,
    collect_narration,
    collect_structured_narration,
    get_gm_characters,
    get_gm_threads,
    get_gm_timeline,
    get_gm_turn_detail,
    get_gm_world,
    get_interventions,
    get_permissions,
    get_run_status,
    get_status,
    list_projects,
    request_stop,
    resolve_project_dir,
    run_turn,
    start_auto_run,
    submit_review,
)


class AutoRequest(BaseModel):
    turns: int = Field(gt=0)


class ReviewRequest(BaseModel):
    decision: ReviewDecision


class TurnRequest(BaseModel):
    """Optional body for ``POST /turn`` (docs/issues/023). Absent/empty body = a plain turn,
    same as before this issue — ``free_text``/``drafts`` pass through verbatim to
    ``TurnPipeline.run``'s ``intervention_text``/``intervention_drafts`` (no reinterpretation)."""

    free_text: str | None = None
    drafts: list[dict[str, Any]] | None = None


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

    @app.get("/api/project/{name}/turns")
    def api_turns(name: str, from_turn: int = Query(1, alias="from", ge=1)) -> list[dict]:
        """Structured per-turn narration: ``[{turn, status, text}]`` (docs/issues/021-022)."""
        project_yaml = _project_yaml(name)
        try:
            entries = collect_structured_narration(project_yaml, from_turn)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return [{"turn": e.turn, "status": e.status, "text": e.text} for e in entries]

    @app.post("/api/project/{name}/turn")
    def api_run_turn(name: str, body: TurnRequest | None = None) -> dict:
        """Runs one turn. Optional ``body`` carries a GM intervention (docs/issues/023):
        ``free_text`` goes through the Interpreter, ``drafts`` are direct-input Intervention
        drafts — both forwarded verbatim to ``TurnPipeline.run``, which persists whatever gets
        accepted/rejected to this turn's ``intervention.yaml``. 409 while an ``auto`` run is in
        progress for this project (same one-active-run-per-project rule ``/auto`` enforces)."""
        project_yaml = _project_yaml(name)
        if get_run_status(project_yaml).running:
            raise HTTPException(
                status_code=409, detail=f"an auto run is already in progress for {name}"
            )
        free_text = body.free_text if body is not None else None
        drafts = body.drafts if body is not None else None
        try:
            result = run_turn(project_yaml, intervention_text=free_text, intervention_drafts=drafts)
        except UnresolvedTurnError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LoadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "turn": result.turn,
            "status": result.status.value,
            "turn_dir": str(result.turn_dir),
        }

    @app.post("/api/project/{name}/auto")
    def api_start_auto(name: str, body: AutoRequest) -> dict:
        project_yaml = _project_yaml(name)
        try:
            start_auto_run(project_yaml, body.turns)
        except AutoRunAlreadyRunningError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"started": True, "turns": body.turns}

    @app.get("/api/project/{name}/run_status")
    def api_run_status(name: str) -> dict:
        project_yaml = _project_yaml(name)
        status = get_run_status(project_yaml)
        return {
            "running": status.running,
            "current_turn": status.current_turn,
            "last_status": status.last_status,
            "stopped_reason": status.stopped_reason,
        }

    @app.post("/api/project/{name}/stop")
    def api_stop(name: str) -> dict:
        project_yaml = _project_yaml(name)
        request_stop(project_yaml)
        return {"stopping": True}

    @app.post("/api/project/{name}/review")
    def api_review(name: str, body: ReviewRequest) -> dict:
        if body.decision not in (ReviewDecision.ACCEPT_ALL, ReviewDecision.REJECT_ALL):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"unsupported decision over the API: {body.decision.value!r} "
                    "(only accept_all/reject_all — richer decisions stay CLI-only)"
                ),
            )
        project_yaml = _project_yaml(name)
        try:
            result = submit_review(project_yaml, body.decision)
        except NoPendingReviewError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ReviewStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "decision": result.decision.value,
            "resulting_turn_status": getattr(
                result.resulting_turn_status, "value", result.resulting_turn_status
            ),
            "turn_dir": str(result.turn_dir),
        }

    @app.get("/api/project/{name}/permissions")
    def api_permissions(name: str) -> dict:
        """``user_mode`` and the intervention types it may submit (docs/issues/023, D114) — the
        UI uses ``allowed_types`` to limit the structured-intervention form's type select."""
        project_yaml = _project_yaml(name)
        try:
            info = get_permissions(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return {"user_mode": info.user_mode, "allowed_types": info.allowed_types}

    @app.get("/api/project/{name}/interventions")
    def api_interventions(name: str) -> dict:
        """Project-wide intervention history + the most recent turn's accepted/rejected
        interventions, rejection reasons included (docs/issues/023)."""
        project_yaml = _project_yaml(name)
        try:
            info = get_interventions(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return {"history": info.history, "last_turn": info.last_turn}

    @app.get("/api/project/{name}/gm/characters")
    def api_gm_characters(name: str) -> list[dict]:
        """Omniscient character dump (emotions/goals/knowledge/secrets/private_mind/speech/
        status + each character's outgoing relationships) for the GM pane (docs/issues/024)."""
        project_yaml = _project_yaml(name)
        try:
            return get_gm_characters(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None

    @app.get("/api/project/{name}/gm/world")
    def api_gm_world(name: str) -> dict:
        """World summary/parameters, threat pressure tracks (with next uncrossed stage),
        pacing config, and full scene state incl. ``hidden_facts`` (docs/issues/024)."""
        project_yaml = _project_yaml(name)
        try:
            info = get_gm_world(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return {
            "world": info.world,
            "threats": info.threats,
            "pacing": info.pacing,
            "scenes": info.scenes,
        }

    @app.get("/api/project/{name}/gm/timeline")
    def api_gm_timeline(
        name: str,
        from_turn: int = Query(1, alias="from", ge=1),
        limit: int = Query(50, ge=1),
    ) -> list[dict]:
        """Timeline entries from ``from`` turn onward (up to ``limit``), each with its
        hydrated ``events.yaml`` bodies incl. visibility (docs/issues/024)."""
        project_yaml = _project_yaml(name)
        try:
            return get_gm_timeline(project_yaml, from_turn, limit)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None

    @app.get("/api/project/{name}/gm/threads")
    def api_gm_threads(name: str) -> dict:
        """``unresolved_threads`` (full fields) + ``memory_summaries`` (docs/issues/024)."""
        project_yaml = _project_yaml(name)
        try:
            info = get_gm_threads(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return {"threads": info.threads, "memory_summaries": info.memory_summaries}

    @app.get("/api/project/{name}/gm/turn/{turn}")
    def api_gm_turn(name: str, turn: int) -> dict:
        """That turn's ``rolls.yaml``/``checks.yaml``/``state_diff.yaml`` contents
        (docs/issues/024). 404 if the turn directory does not exist."""
        project_yaml = _project_yaml(name)
        try:
            detail = get_gm_turn_detail(project_yaml, turn)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        if detail is None:
            raise HTTPException(status_code=404, detail=f"turn not found: {turn}")
        return detail

    return app
