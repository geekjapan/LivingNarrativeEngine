"""Turn-controls web layer tests (docs/issues/021-022): auto runs, stop, review, structured
narration. Skips entirely when the optional ``web`` extra (fastapi/uvicorn) is not installed —
the core suite must not depend on it."""

import time

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import living_narrative.web.app as web_app  # noqa: E402
import living_narrative.web.service as service  # noqa: E402
from living_narrative.state.transaction import ProjectLockError  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402

_POLL_TIMEOUT_S = 5.0
_POLL_INTERVAL_S = 0.02


def _client(root):
    return TestClient(create_app(root))


def _wait_until(predicate, *, timeout=_POLL_TIMEOUT_S, interval=_POLL_INTERVAL_S):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def _slow_pipeline(monkeypatch, delay=0.05):
    """Make each TurnPipeline.run take ``delay`` seconds, so a background auto-run gives the
    test thread a reliable window to observe it mid-flight (double-start / stop-mid-run)."""
    original_run = service.TurnPipeline.run

    def slow_run(self, *args, **kwargs):
        time.sleep(delay)
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(service.TurnPipeline, "run", slow_run)


def _write_stopped_for_review_turn(project_path, *, turn=1, changes=None):
    changes = (
        changes
        if changes is not None
        else [
            {
                "target": "world",
                "op": "set",
                "path": "summary",
                "value": "reviewed summary",
                "visibility": "canon",
            }
        ]
    )
    runs_dir = project_path.parent / "workspace" / "runs"
    turn_dir = runs_dir / f"turn_{turn:04d}"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump({"status": "stopped_for_review", "rng_draws_consumed": 0}),
        encoding="utf-8",
    )
    (turn_dir / "state_diff.yaml").write_text(
        yaml.safe_dump(
            {
                "diff": {"id": f"diff_{turn:04d}", "turn": turn, "changes": changes},
                "rejected_changes": [],
                "applied": False,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return turn_dir


# --- auto happy path -----------------------------------------------------------------


def test_auto_runs_n_turns_to_completion(tmp_path, build_project):
    build_project(tmp_path)
    client = _client(tmp_path)

    response = client.post("/api/project/project/auto", json={"turns": 2})
    assert response.status_code == 200
    assert response.json() == {"started": True, "turns": 2}

    completed = _wait_until(
        lambda: not client.get("/api/project/project/run_status").json()["running"]
    )
    assert completed

    final = client.get("/api/project/project/run_status").json()
    assert final["running"] is False
    assert final["current_turn"] >= 1
    assert final["stopped_reason"] in {"turns_complete", "stopped_for_review", "pending_review"}


def test_run_status_before_any_auto_run(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).get("/api/project/project/run_status")

    assert response.status_code == 200
    assert response.json() == {
        "running": False,
        "current_turn": 0,
        "last_status": None,
        "stopped_reason": None,
    }


# --- double auto -> 409 ---------------------------------------------------------------


def test_second_auto_while_running_is_409(tmp_path, build_project, monkeypatch):
    _slow_pipeline(monkeypatch, delay=0.2)
    build_project(tmp_path)
    client = _client(tmp_path)

    first = client.post("/api/project/project/auto", json={"turns": 5})
    assert first.status_code == 200

    second = client.post("/api/project/project/auto", json={"turns": 5})
    assert second.status_code == 409

    # let the background run finish so it doesn't leak into other tests via the module-level
    # registry (keyed by resolved project dir, which is unique per tmp_path anyway, but be tidy).
    client.post("/api/project/project/stop")
    _wait_until(lambda: not client.get("/api/project/project/run_status").json()["running"])


# --- stop mid-run ----------------------------------------------------------------------


def test_stop_halts_at_a_turn_boundary(tmp_path, build_project, monkeypatch):
    _slow_pipeline(monkeypatch, delay=0.1)
    build_project(tmp_path)
    client = _client(tmp_path)

    response = client.post("/api/project/project/auto", json={"turns": 50})
    assert response.status_code == 200

    started = _wait_until(
        lambda: client.get("/api/project/project/run_status").json()["current_turn"] >= 1
    )
    assert started

    stop_response = client.post("/api/project/project/stop")
    assert stop_response.status_code == 200

    completed = _wait_until(
        lambda: not client.get("/api/project/project/run_status").json()["running"]
    )
    assert completed

    final = client.get("/api/project/project/run_status").json()
    assert final["current_turn"] < 50
    assert final["stopped_reason"] == "stopped"


# --- review flow -------------------------------------------------------------------------


def test_review_accept_all_via_api_unblocks_next_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_stopped_for_review_turn(project_path, turn=1)
    client = _client(tmp_path)

    status_before = client.get("/api/project/project/status").json()
    assert status_before["pending_review"] is True
    assert status_before["pending_review_turn"] == 1

    review_response = client.post("/api/project/project/review", json={"decision": "accept_all"})
    assert review_response.status_code == 200
    data = review_response.json()
    assert data["decision"] == "accept_all"
    assert data["resulting_turn_status"] == "applied"

    turn_response = client.post("/api/project/project/turn")
    assert turn_response.status_code == 200
    assert turn_response.json()["turn"] == 2


def test_review_reject_all_via_api_unblocks_next_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_stopped_for_review_turn(project_path, turn=1)
    client = _client(tmp_path)

    review_response = client.post("/api/project/project/review", json={"decision": "reject_all"})
    assert review_response.status_code == 200
    assert review_response.json()["resulting_turn_status"] == "applied"

    turn_response = client.post("/api/project/project/turn")
    assert turn_response.status_code == 200
    assert turn_response.json()["turn"] == 2


def test_review_with_no_pending_turn_is_409(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).post(
        "/api/project/project/review", json={"decision": "accept_all"}
    )

    assert response.status_code == 409


def test_turn_returns_409_for_project_lock_conflict(tmp_path, build_project, monkeypatch):
    build_project(tmp_path)

    def locked_run(*_args, **_kwargs):
        raise ProjectLockError("project is already locked")

    monkeypatch.setattr(web_app, "run_turn", locked_run)

    response = _client(tmp_path).post("/api/project/project/turn")

    assert response.status_code == 409
    assert response.json()["detail"] == "project is already locked"


def test_review_returns_409_for_project_lock_conflict(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path)
    _write_stopped_for_review_turn(project_path)

    def locked_review(*_args, **_kwargs):
        raise ProjectLockError("project is already locked")

    monkeypatch.setattr(web_app, "submit_review", locked_review)

    response = _client(tmp_path).post(
        "/api/project/project/review", json={"decision": "accept_all"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "project is already locked"


def test_review_rejects_unsupported_decisions_over_the_api(tmp_path, build_project):
    """``partial`` is exposed over the API as of docs/issues/025 — ``edit``/``rerun_turn``
    (which need a hand-edited diff / RNG replay, no web surface for either) still are not."""
    project_path = build_project(tmp_path)
    _write_stopped_for_review_turn(project_path, turn=1)

    response = _client(tmp_path).post("/api/project/project/review", json={"decision": "edit"})

    assert response.status_code == 400


def test_review_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).post(
        "/api/project/does-not-exist/review", json={"decision": "accept_all"}
    )

    assert response.status_code == 404


# --- structured narration ----------------------------------------------------------------


def test_turns_endpoint_includes_status(tmp_path, build_project):
    project_path = build_project(tmp_path)
    from living_narrative.pipeline import TurnPipeline

    result = TurnPipeline().run(project_path)

    response = _client(tmp_path).get("/api/project/project/turns")

    assert response.status_code == 200
    data = response.json()
    assert data == [{"turn": 1, "status": result.status.value, "text": data[0]["text"]}]


def test_turns_endpoint_reflects_stopped_for_review_status(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_stopped_for_review_turn(project_path, turn=1)

    response = _client(tmp_path).get("/api/project/project/turns")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["status"] == "stopped_for_review"


def test_turns_endpoint_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/turns")

    assert response.status_code == 404


def test_auto_start_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).post("/api/project/does-not-exist/auto", json={"turns": 1})

    assert response.status_code == 404


def test_auto_rejects_non_positive_turns(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).post("/api/project/project/auto", json={"turns": 0})

    assert response.status_code == 422
