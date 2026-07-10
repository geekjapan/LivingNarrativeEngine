"""Settings API/UI regression tests for issue 046."""

from pathlib import Path

import pytest
import yaml

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.web import service  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402


def _client(root: Path) -> TestClient:
    return TestClient(create_app(root))


def test_settings_page_and_api_show_editable_yaml(tmp_path, build_project):
    build_project(tmp_path)
    client = _client(tmp_path)

    page = client.get("/").text
    project = client.get("/api/project/project/settings/project.yaml")
    pricing = client.get("/api/project/project/settings/pricing.yaml")

    assert "LLM profiles / bindings" in page
    assert "モデル価格" in page
    assert project.status_code == 200
    assert set(yaml.safe_load(project.json()["yaml"])) == {"llm_profiles", "llm_bindings"}
    assert yaml.safe_load(pricing.json()["yaml"]) == {}


def test_valid_settings_round_trip_preserves_other_project_fields(tmp_path, build_project):
    project_path = build_project(tmp_path, title="残す題名")
    client = _client(tmp_path)
    settings = {
        "llm_profiles": {
            "writer": {
                "provider": "mock",
                "model": "writer-v2",
                "timeout_seconds": 45,
                "prompt_recording": "hash_only",
            }
        },
        "llm_bindings": {"narrator": "writer"},
    }

    response = client.put(
        "/api/project/project/settings/project.yaml",
        json={"yaml": yaml.safe_dump(settings)},
    )

    assert response.status_code == 200
    assert yaml.safe_load(response.json()["yaml"]) == settings
    saved = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert saved["title"] == "残す題名"
    assert saved["llm_bindings"] == {"narrator": "writer"}


def test_valid_pricing_round_trip(tmp_path, build_project):
    build_project(tmp_path)
    pricing = {"writer-v2": {"input_usd_per_1m": 1.25, "output_usd_per_1m": 2.5}}
    client = _client(tmp_path)

    response = client.put(
        "/api/project/project/settings/pricing.yaml",
        json={"yaml": yaml.safe_dump(pricing)},
    )

    assert response.status_code == 200
    assert yaml.safe_load(response.json()["yaml"]) == pricing
    assert (
        yaml.safe_load((tmp_path / "project" / "pricing.yaml").read_text(encoding="utf-8"))
        == pricing
    )


@pytest.mark.parametrize(
    ("filename", "text", "expected"),
    [
        ("project.yaml", "llm_profiles: [", "invalid YAML"),
        (
            "project.yaml",
            "llm_profiles: {}\nllm_bindings:\n  narrator: missing\n",
            "undefined llm_profiles",
        ),
        (
            "pricing.yaml",
            "model-x:\n  input_usd_per_1m: free\n  output_usd_per_1m: 2\n",
            "invalid pricing.yaml",
        ),
    ],
)
def test_invalid_settings_are_rejected_without_changing_file(
    tmp_path, build_project, filename, text, expected
):
    project_path = build_project(tmp_path)
    path = project_path.parent / filename
    if filename == "pricing.yaml":
        path.write_text("model-old:\n  input_usd_per_1m: 1\n  output_usd_per_1m: 2\n")
    before = path.read_bytes()

    response = _client(tmp_path).put(
        f"/api/project/project/settings/{filename}", json={"yaml": text}
    )

    assert response.status_code == 400
    assert expected in response.json()["detail"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("filename", ["..%2Fsecret.yaml", "state/world.yaml", "other.yaml"])
def test_settings_api_rejects_path_traversal_and_non_fixed_files(tmp_path, build_project, filename):
    build_project(tmp_path)

    response = _client(tmp_path).put(
        f"/api/project/project/settings/{filename}", json={"yaml": "stolen: true"}
    )

    assert response.status_code == 400
    assert "unsupported settings file" in response.json()["detail"]


def test_settings_write_uses_temporary_sibling_then_replace(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path)
    replaced = []
    real_replace = service.os.replace

    def recording_replace(source, destination):
        replaced.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(service.os, "replace", recording_replace)

    response = _client(tmp_path).put(
        "/api/project/project/settings/pricing.yaml",
        json={"yaml": "model-x:\n  input_usd_per_1m: 1\n  output_usd_per_1m: 2\n"},
    )

    assert response.status_code == 200
    assert replaced == [
        (project_path.parent / "pricing.yaml.tmp", project_path.parent / "pricing.yaml")
    ]
