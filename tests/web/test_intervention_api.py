"""Intervention Input web layer tests (docs/issues/023, Track B). Skips entirely when the
optional ``web`` extra (fastapi/uvicorn) is not installed — the core suite must not depend on it.
"""

import time

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import living_narrative.web.service as service  # noqa: E402
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


def _set_user_mode(project_path, mode: str) -> None:
    data = yaml.safe_load(project_path.read_text(encoding="utf-8")) or {}
    data["user_mode"] = mode
    project_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _slow_pipeline(monkeypatch, delay=0.2):
    original_run = service.TurnPipeline.run

    def slow_run(self, *args, **kwargs):
        time.sleep(delay)
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(service.TurnPipeline, "run", slow_run)


# --- free text ---------------------------------------------------------------------------


def test_free_text_intervention_recorded_in_intervention_yaml(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")  # full_gm allows every intervention type
    client = _client(tmp_path)

    response = client.post(
        "/api/project/project/turn", json={"free_text": "扉を開けて次の部屋に進んでほしい"}
    )

    assert response.status_code == 200
    turn = response.json()["turn"]
    intervention_path = (
        tmp_path / "project" / "workspace" / "runs" / f"turn_{turn:04d}" / "intervention.yaml"
    )
    assert intervention_path.exists()
    data = yaml.safe_load(intervention_path.read_text(encoding="utf-8"))
    assert len(data["interventions"]) + len(data["rejections"]) >= 1
    # full_gm allows every type, so the interpreted draft must have been accepted, not rejected.
    assert len(data["interventions"]) == 1
    assert data["rejections"] == []


# --- structured drafts ---------------------------------------------------------------------


def test_full_gm_draft_is_accepted(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")
    client = _client(tmp_path)

    response = client.post(
        "/api/project/project/turn",
        json={
            "drafts": [
                {
                    "type": "scene_directive",
                    "target": {"kind": "scene", "id": "scene_001"},
                    "content": "緊張感を高めて",
                    "visibility": "gm_only",
                }
            ]
        },
    )

    assert response.status_code == 200
    turn = response.json()["turn"]
    intervention_path = (
        tmp_path / "project" / "workspace" / "runs" / f"turn_{turn:04d}" / "intervention.yaml"
    )
    data = yaml.safe_load(intervention_path.read_text(encoding="utf-8"))
    assert data["rejections"] == []
    assert len(data["interventions"]) == 1
    assert data["interventions"][0]["type"] == "scene_directive"


def test_watcher_draft_is_rejected_and_recorded(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "watcher")
    client = _client(tmp_path)

    response = client.post(
        "/api/project/project/turn",
        json={
            "drafts": [
                {
                    "type": "canon_edit",
                    "target": {"kind": "canon"},
                    "content": "世界観の根本を書き換える",
                    "visibility": "canon",
                }
            ]
        },
    )

    assert response.status_code == 200
    turn = response.json()["turn"]
    intervention_path = (
        tmp_path / "project" / "workspace" / "runs" / f"turn_{turn:04d}" / "intervention.yaml"
    )
    data = yaml.safe_load(intervention_path.read_text(encoding="utf-8"))
    assert data["interventions"] == []
    assert len(data["rejections"]) == 1
    assert data["rejections"][0]["type"] == "canon_edit"
    assert data["rejections"][0]["requested_user_mode"] == "watcher"


# --- permissions endpoint ------------------------------------------------------------------


def test_permissions_endpoint_reflects_assistant_gm_default(tmp_path, build_project):
    build_project(tmp_path)  # default user_mode: assistant_gm

    response = _client(tmp_path).get("/api/project/project/permissions")

    assert response.status_code == 200
    data = response.json()
    assert data["user_mode"] == "assistant_gm"
    assert "scene_directive" in data["allowed_types"]
    assert "canon_edit" not in data["allowed_types"]  # universal invariant: full_gm/god only


def test_permissions_endpoint_reflects_watcher_mode(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "watcher")

    response = _client(tmp_path).get("/api/project/project/permissions")

    assert response.status_code == 200
    data = response.json()
    assert data["user_mode"] == "watcher"
    assert data["allowed_types"] == []


def test_permissions_endpoint_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/permissions")

    assert response.status_code == 404


# --- interventions history endpoint ---------------------------------------------------------


def test_interventions_endpoint_reports_history_and_last_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")
    client = _client(tmp_path)

    turn_response = client.post(
        "/api/project/project/turn",
        json={
            "drafts": [
                {
                    "type": "scene_directive",
                    "target": {"kind": "scene", "id": "scene_001"},
                    "content": "静けさを強調して",
                    "visibility": "gm_only",
                }
            ]
        },
    )
    assert turn_response.status_code == 200
    turn = turn_response.json()["turn"]

    response = client.get("/api/project/project/interventions")

    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 1
    assert data["history"][0]["type"] == "scene_directive"
    assert data["history"][0]["turn"] == turn
    assert data["last_turn"]["turn"] == turn
    assert len(data["last_turn"]["interventions"]) == 1
    assert data["last_turn"]["rejections"] == []


def test_interventions_endpoint_before_any_turn(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).get("/api/project/project/interventions")

    assert response.status_code == 200
    assert response.json() == {"history": [], "last_turn": None}


def test_interventions_endpoint_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/interventions")

    assert response.status_code == 404


# --- 409 while auto is running ---------------------------------------------------------------


def test_turn_returns_409_while_auto_run_is_active(tmp_path, build_project, monkeypatch):
    _slow_pipeline(monkeypatch, delay=0.2)
    build_project(tmp_path)
    client = _client(tmp_path)

    auto_response = client.post("/api/project/project/auto", json={"turns": 5})
    assert auto_response.status_code == 200

    turn_response = client.post("/api/project/project/turn")
    assert turn_response.status_code == 409

    client.post("/api/project/project/stop")
    _wait_until(lambda: not client.get("/api/project/project/run_status").json()["running"])


# --- backward compatibility: no body ---------------------------------------------------------


def test_turn_with_no_body_still_works(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).post("/api/project/project/turn")

    assert response.status_code == 200
    assert response.json()["turn"] == 1


def test_turn_with_empty_body_still_works(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).post("/api/project/project/turn", json={})

    assert response.status_code == 200
    assert response.json()["turn"] == 1
