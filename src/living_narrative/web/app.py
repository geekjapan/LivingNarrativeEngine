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

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from living_narrative.pipeline import LoadError, UnresolvedTurnError
from living_narrative.session.mode import is_gm_vault_visible
from living_narrative.session.review import ReviewDecision, ReviewStateError
from living_narrative.web.page import INDEX_HTML
from living_narrative.web.service import (
    AutoRunAlreadyRunningError,
    NoPendingReviewError,
    ProjectNotFoundError,
    SettingsValidationError,
    collect_narration,
    collect_structured_narration,
    get_gm_characters,
    get_gm_threads,
    get_gm_timeline,
    get_gm_turn_detail,
    get_gm_world,
    get_interventions,
    get_permissions,
    get_review_status,
    get_run_status,
    get_settings_yaml,
    get_status,
    list_projects,
    request_stop,
    resolve_project_dir,
    run_turn,
    start_auto_run,
    submit_review,
    update_settings_yaml,
)

_WEB_REVIEW_DECISIONS = (
    ReviewDecision.ACCEPT_ALL,
    ReviewDecision.REJECT_ALL,
    ReviewDecision.PARTIAL,
)


class AutoRequest(BaseModel):
    turns: int = Field(gt=0)


class ReviewRequest(BaseModel):
    """Body for ``POST .../review`` (docs/issues/025). ``selected_indexes`` is only meaningful
    (and required, non-empty) for ``decision: partial`` — it refers to the ``index`` field
    ``GET .../review`` attaches to each proposed change."""

    decision: ReviewDecision
    selected_indexes: list[int] = Field(default_factory=list)


class TurnRequest(BaseModel):
    """Optional body for ``POST /turn`` (docs/issues/023). Absent/empty body = a plain turn,
    same as before this issue — ``free_text``/``drafts`` pass through verbatim to
    ``TurnPipeline.run``'s ``intervention_text``/``intervention_drafts`` (no reinterpretation)."""

    free_text: str | None = None
    drafts: list[dict[str, Any]] | None = None


class SettingsRequest(BaseModel):
    yaml: str


def create_app(project_root: Path) -> FastAPI:
    """Build the FastAPI app scoped to ``project_root`` (the directory ``serve`` was given).

    ``project_root`` is fixed at app-creation time (not a per-request parameter): every
    ``{name}`` path parameter below is resolved as a single path segment directly under it, so
    a client can only ever reach projects the operator chose to serve.
    """
    app = FastAPI(title="Living Narrative Engine — Web UI")

    @app.middleware("http")
    async def check_mutation_origin(request: Request, call_next):
        if request.method in {"POST", "PUT"}:
            origin = request.headers.get("origin")
            allowed_origin = f"http://127.0.0.1:{request.url.port}"
            if origin is not None and origin != allowed_origin:
                return JSONResponse(status_code=403, content={"detail": "origin not allowed"})
        return await call_next(request)

    def _project_yaml(name: str) -> Path:
        try:
            project_dir = resolve_project_dir(project_root, name)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return project_dir / "project.yaml"

    def _require_sensitive_session_access(project_yaml: Path) -> None:
        info = get_permissions(project_yaml)
        if info.user_mode == "player_character":
            raise HTTPException(status_code=403, detail="sensitive session view is unavailable")

    def _require_gm_vault_access(project_yaml: Path) -> None:
        info = get_permissions(project_yaml)
        if not is_gm_vault_visible(info.user_mode):
            raise HTTPException(status_code=403, detail="GM-only view is unavailable")

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
            "visible_facts": status.visible_facts,
            "llm_usage": status.llm_usage.model_dump(mode="json"),
        }

    @app.get("/api/project/{name}/settings/{filename:path}")
    def api_get_settings(name: str, filename: str) -> dict[str, str]:
        project_yaml = _project_yaml(name)
        _require_sensitive_session_access(project_yaml)
        try:
            return {"filename": filename, "yaml": get_settings_yaml(project_yaml, filename)}
        except SettingsValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/project/{name}/settings/{filename:path}")
    def api_update_settings(name: str, filename: str, body: SettingsRequest) -> dict[str, str]:
        project_yaml = _project_yaml(name)
        _require_sensitive_session_access(project_yaml)
        try:
            saved = update_settings_yaml(project_yaml, filename, body.yaml)
        except (OSError, SettingsValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"filename": filename, "yaml": saved}

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

    @app.get("/api/project/{name}/review")
    def api_get_review(name: str) -> dict:
        """The latest pending/stopped-for-review turn's proposed diff, for the diff-review UI
        (docs/issues/025): each change carries its list ``index`` (what ``selected_indexes``
        below refers to), plus rejected-change candidates and this turn's check findings.
        ``pending: false`` (no turn/status/changes) when nothing is awaiting review."""
        project_yaml = _project_yaml(name)
        _require_sensitive_session_access(project_yaml)
        try:
            info = get_review_status(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        return {
            "pending": info.pending,
            "turn": info.turn,
            "status": info.status,
            "changes": info.changes,
            "rejected_changes": info.rejected_changes,
            "checks": info.checks,
        }

    @app.post("/api/project/{name}/review")
    def api_review(name: str, body: ReviewRequest) -> dict:
        """Resolve the pending-review turn (docs/issues/021-022, extended by 025 to expose
        ``partial``). ``partial`` requires a non-empty ``selected_indexes`` (422 otherwise) and
        delegates to the same ``session.review.resolve_review`` primitive the CLI's
        ``review --decision partial --apply`` uses — no separate resolution logic here."""
        project_yaml = _project_yaml(name)
        _require_sensitive_session_access(project_yaml)
        if body.decision not in _WEB_REVIEW_DECISIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"unsupported decision over the API: {body.decision.value!r} "
                    "(only accept_all/reject_all/partial — edit/rerun_turn stay CLI-only)"
                ),
            )
        if body.decision == ReviewDecision.PARTIAL and not body.selected_indexes:
            raise HTTPException(
                status_code=422,
                detail="decision=partial requires a non-empty selected_indexes",
            )
        selected_indices = (
            set(body.selected_indexes) if body.decision == ReviewDecision.PARTIAL else None
        )
        try:
            result = submit_review(project_yaml, body.decision, selected_indices=selected_indices)
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
        _require_sensitive_session_access(project_yaml)
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
        _require_gm_vault_access(project_yaml)
        try:
            return get_gm_characters(project_yaml)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None

    @app.get("/api/project/{name}/gm/world")
    def api_gm_world(name: str) -> dict:
        """World summary/parameters, threat pressure tracks (with next uncrossed stage),
        pacing config, and full scene state incl. ``hidden_facts`` (docs/issues/024)."""
        project_yaml = _project_yaml(name)
        _require_gm_vault_access(project_yaml)
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
        _require_gm_vault_access(project_yaml)
        try:
            return get_gm_timeline(project_yaml, from_turn, limit)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None

    @app.get("/api/project/{name}/gm/threads")
    def api_gm_threads(name: str) -> dict:
        """``unresolved_threads`` (full fields) + ``memory_summaries`` (docs/issues/024)."""
        project_yaml = _project_yaml(name)
        _require_gm_vault_access(project_yaml)
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
        _require_gm_vault_access(project_yaml)
        try:
            detail = get_gm_turn_detail(project_yaml, turn)
        except ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"project not found: {name}") from None
        if detail is None:
            raise HTTPException(status_code=404, detail=f"turn not found: {turn}")
        return detail

    return app
