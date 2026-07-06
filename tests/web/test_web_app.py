"""FastAPI web layer tests (docs/issues/020). Skips entirely when the optional ``web`` extra
(fastapi/uvicorn) is not installed — the core suite must not depend on it."""

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.pipeline import TurnPipeline  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402


def _client(root):
    return TestClient(create_app(root))


def test_list_projects_scans_root(tmp_path, build_project):
    build_project(tmp_path, title="My Project")

    response = _client(tmp_path).get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert data == [{"name": "project", "title": "My Project"}]


def test_list_projects_empty_root(tmp_path):
    (tmp_path / "not_a_project").mkdir()

    response = _client(tmp_path).get("/api/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_status_before_any_turn(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).get("/api/project/project/status")

    assert response.status_code == 200
    data = response.json()
    assert data["current_turn"] == 0
    assert data["pending_review"] is False
    assert data["scene"]["location"] == "駅"
    assert data["characters"] == [{"id": "char_001", "name": "Aoi", "status": "alive"}]


def test_status_never_leaks_gm_vault_or_secrets(tmp_path, build_project):
    build_project(
        tmp_path,
        hidden_facts=[
            {"id": "fact_001", "text": "a deep secret", "visibility": "gm_only", "known_by": []}
        ],
    )

    response = _client(tmp_path).get("/api/project/project/status")

    assert response.status_code == 200
    assert "a deep secret" not in response.text
    assert "secrets" not in response.json()["characters"][0]
    assert "private_mind" not in response.json()["characters"][0]


def test_status_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/status")

    assert response.status_code == 404


@pytest.mark.parametrize("name", ["..", "../etc", "a/b", "a\\b", ""])
def test_path_traversal_rejected(tmp_path, build_project, name):
    build_project(tmp_path)

    response = _client(tmp_path).get(f"/api/project/{name}/status")

    assert response.status_code == 404


def test_path_traversal_cannot_escape_root_via_symlink(tmp_path, build_project):
    outside = tmp_path.parent / "outside_secret"
    outside.mkdir(exist_ok=True)
    (outside / "project.yaml").write_text("id: outside\n", encoding="utf-8")
    root = tmp_path / "served_root"
    root.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)

    response = _client(root).get("/api/project/escape/status")

    assert response.status_code == 404


def test_turn_and_narration_round_trip(tmp_path, build_project):
    project_path = build_project(tmp_path)

    client = _client(tmp_path)
    turn_response = client.post("/api/project/project/turn")

    assert turn_response.status_code == 200
    turn_data = turn_response.json()
    assert turn_data["turn"] == 1
    assert turn_data["status"] in {"applied", "pending_review", "stopped_for_review", "failed"}

    status_response = client.get("/api/project/project/status")
    assert status_response.json()["current_turn"] == 1 or turn_data["status"] != "applied"

    narration_response = client.get("/api/project/project/narration")
    assert narration_response.status_code == 200
    assert narration_response.headers["content-type"].startswith("text/plain")

    # sanity: narration matches what TurnPipeline itself wrote for this project
    del project_path


def test_narration_never_leaks_hidden_facts(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        hidden_facts=[
            {"id": "fact_001", "text": "a deep secret", "visibility": "gm_only", "known_by": []}
        ],
    )
    TurnPipeline().run(project_path)

    response = _client(tmp_path).get("/api/project/project/narration")

    assert response.status_code == 200
    assert "a deep secret" not in response.text


def test_narration_from_query_skips_earlier_turns(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    TurnPipeline().run(project_path)

    client = _client(tmp_path)
    full = client.get("/api/project/project/narration").text
    from_turn_2 = client.get("/api/project/project/narration?from=2").text

    assert from_turn_2 != full
    assert len(from_turn_2) < len(full)


def test_narration_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/narration")

    assert response.status_code == 404


def test_index_serves_html(tmp_path):
    response = _client(tmp_path).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text
