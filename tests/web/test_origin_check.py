"""Origin checks for mutation endpoints (docs/issues/065)."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.web.app import create_app  # noqa: E402


def _client(root, *, port=None):
    if port is None:
        return TestClient(create_app(root))
    return TestClient(create_app(root), base_url=f"http://127.0.0.1:{port}")


def test_mutation_without_origin_is_allowed(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).put(
        "/api/project/project/settings/pricing.yaml",
        json={"yaml": "model-x:\n  input_usd_per_1m: 1\n  output_usd_per_1m: 2\n"},
    )

    assert response.status_code == 200


def test_configured_loopback_origin_is_allowed(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path, port=9876).put(
        "/api/project/project/settings/pricing.yaml",
        headers={"Origin": "http://127.0.0.1:9876"},
        json={"yaml": "{}\n"},
    )

    assert response.status_code == 200


def test_localhost_origin_is_allowed(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path, port=9876).put(
        "/api/project/project/settings/pricing.yaml",
        headers={"Origin": "http://localhost:9876"},
        json={"yaml": "{}\n"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("POST", "/api/project/project/turn", {}),
        ("POST", "/api/project/project/auto", {"json": {"turns": 1}}),
        ("POST", "/api/project/project/stop", {}),
        ("POST", "/api/project/project/review", {"json": {"decision": "accept_all"}}),
        (
            "PUT",
            "/api/project/project/settings/pricing.yaml",
            {"json": {"yaml": "{}\n"}},
        ),
    ],
)
def test_cross_origin_mutations_are_rejected(tmp_path, build_project, method, path, kwargs):
    build_project(tmp_path)

    response = _client(tmp_path).request(
        method,
        path,
        headers={"Origin": "https://evil.example"},
        **kwargs,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "origin not allowed"}
