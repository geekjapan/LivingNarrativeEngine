"""State Diff Review UI web layer tests (docs/issues/025): GET/POST .../review with the
``partial`` decision exposed alongside ``accept_all``/``reject_all``. Skips entirely when the
optional ``web`` extra (fastapi/uvicorn) is not installed — the core suite must not depend on it.
"""

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.state.store import StateStore  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402

_DEFAULT_CHANGES = [
    {
        "target": "world",
        "op": "set",
        "path": "summary",
        "value": "reviewed summary",
        "visibility": "canon",
    },
    {
        "target": "world",
        "op": "set",
        "path": "name",
        "value": "Reviewed World",
        "visibility": "canon",
    },
]


def _client(root):
    return TestClient(create_app(root))


def _write_pending_turn(
    project_path,
    *,
    turn=1,
    status="stopped_for_review",
    changes=None,
    rejected_changes=None,
    findings=None,
):
    changes = _DEFAULT_CHANGES if changes is None else changes
    rejected_changes = rejected_changes or []
    runs_dir = project_path.parent / "workspace" / "runs"
    turn_dir = runs_dir / f"turn_{turn:04d}"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump({"status": status, "rng_draws_consumed": 0}),
        encoding="utf-8",
    )
    (turn_dir / "state_diff.yaml").write_text(
        yaml.safe_dump(
            {
                "diff": {"id": f"diff_{turn:04d}", "turn": turn, "changes": changes},
                "rejected_changes": rejected_changes,
                "applied": False,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    if findings is not None:
        (turn_dir / "checks.yaml").write_text(
            yaml.safe_dump({"findings": findings}, allow_unicode=True),
            encoding="utf-8",
        )
    return turn_dir


def _state_dir(project_path):
    return project_path.parent / "workspace" / "state"


# --- GET .../review ------------------------------------------------------------------------


def test_get_review_not_pending_shape(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).get("/api/project/project/review")

    assert response.status_code == 200
    assert response.json() == {
        "pending": False,
        "turn": None,
        "status": None,
        "changes": [],
        "rejected_changes": [],
        "checks": [],
    }


def test_get_review_pending_shape(tmp_path, build_project):
    project_path = build_project(tmp_path)
    rejected = [
        {
            "change": {
                "target": "world",
                "op": "set",
                "path": "summary",
                "value": "declined",
                "visibility": "canon",
            },
            "reason": "低確度",
        }
    ]
    findings = [{"checker": "leak_check", "severity": "warn", "message": "leak suspected"}]
    _write_pending_turn(project_path, turn=1, rejected_changes=rejected, findings=findings)

    response = _client(tmp_path).get("/api/project/project/review")

    assert response.status_code == 200
    data = response.json()
    assert data["pending"] is True
    assert data["turn"] == 1
    assert data["status"] == "stopped_for_review"
    assert data["changes"] == [
        {
            "index": 0,
            "target": "world",
            "id": None,
            "path": "summary",
            "op": "set",
            "value": "reviewed summary",
            "visibility": "canon",
            "source_event": None,
        },
        {
            "index": 1,
            "target": "world",
            "id": None,
            "path": "name",
            "op": "set",
            "value": "Reviewed World",
            "visibility": "canon",
            "source_event": None,
        },
    ]
    assert data["rejected_changes"] == rejected
    assert len(data["checks"]) == 1
    assert data["checks"][0]["severity"] == "warn"


def test_get_review_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/review")

    assert response.status_code == 404


# --- POST .../review: accept_all / reject_all ----------------------------------------------


def test_review_accept_all_applies_all_changes(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, turn=1)

    response = _client(tmp_path).post(
        "/api/project/project/review", json={"decision": "accept_all"}
    )

    assert response.status_code == 200
    assert response.json()["resulting_turn_status"] == "applied"
    bundle = StateStore.load(_state_dir(project_path))
    assert bundle.world.summary == "reviewed summary"
    assert bundle.world.name == "Reviewed World"


def test_review_reject_all_keeps_state_unchanged(tmp_path, build_project):
    project_path = build_project(tmp_path)
    original = StateStore.load(_state_dir(project_path))
    _write_pending_turn(project_path, turn=1)

    response = _client(tmp_path).post(
        "/api/project/project/review", json={"decision": "reject_all"}
    )

    assert response.status_code == 200
    assert response.json()["resulting_turn_status"] == "applied"
    bundle = StateStore.load(_state_dir(project_path))
    assert bundle.world.summary == original.world.summary
    assert bundle.world.name == original.world.name

    # D120: reject_all still records the turn (status applied), just with no changes applied.
    review_after = _client(tmp_path).get("/api/project/project/review").json()
    assert review_after["pending"] is False


# --- POST .../review: partial ---------------------------------------------------------------


def test_review_partial_applies_only_selected_changes(tmp_path, build_project):
    project_path = build_project(tmp_path)
    original = StateStore.load(_state_dir(project_path))
    _write_pending_turn(project_path, turn=1)

    response = _client(tmp_path).post(
        "/api/project/project/review",
        json={"decision": "partial", "selected_indexes": [0]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "partial"
    assert data["resulting_turn_status"] == "applied"

    bundle = StateStore.load(_state_dir(project_path))
    assert bundle.world.summary == "reviewed summary"
    assert bundle.world.name == original.world.name  # index 1 was not selected

    review_after = _client(tmp_path).get("/api/project/project/review").json()
    assert review_after["pending"] is False


def test_review_partial_requires_non_empty_selected_indexes(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, turn=1)

    response = _client(tmp_path).post(
        "/api/project/project/review",
        json={"decision": "partial", "selected_indexes": []},
    )

    assert response.status_code == 422


def test_review_partial_with_no_pending_turn_is_409(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).post(
        "/api/project/project/review",
        json={"decision": "partial", "selected_indexes": [0]},
    )

    assert response.status_code == 409


def test_review_post_unknown_project_is_404_for_partial(tmp_path):
    response = _client(tmp_path).post(
        "/api/project/does-not-exist/review",
        json={"decision": "partial", "selected_indexes": [0]},
    )

    assert response.status_code == 404
