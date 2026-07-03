from pathlib import Path

import yaml

from living_narrative.state.validation import load_project_config

VALID_PROJECT = {
    "id": "mist_station",
    "title": "霧の駅",
    "genre": "mystery_fantasy",
    "tone": "quiet_ominous",
    "autonomy_level": "assist",
    "user_mode": "assistant_gm",
    "random_seed": "20260703-mist-station",
    "renderer": "novel",
    "llm": {"provider": "mock", "model": "mock-v1"},
    "workspace": {
        "root": "workspace",
        "state": "workspace/state",
        "runs": "workspace/runs",
        "exports": "workspace/exports",
    },
}


def _write_project(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_valid_project_loads_successfully(tmp_path):
    path = _write_project(tmp_path, VALID_PROJECT)
    report = load_project_config(path)
    assert report.is_valid
    assert report.config.title == "霧の駅"
    assert report.errors == []


def test_multiple_invalid_fields_are_aggregated(tmp_path):
    data = {k: v for k, v in VALID_PROJECT.items() if k != "random_seed"}
    data["autonomy_level"] = "not_a_valid_level"
    path = _write_project(tmp_path, data)

    report = load_project_config(path)

    assert not report.is_valid
    fields = {issue.field for issue in report.errors}
    assert "random_seed" in fields
    assert "autonomy_level" in fields
    for issue in report.errors:
        assert issue.path == path


def test_unknown_field_warns_but_still_loads(tmp_path):
    data = {**VALID_PROJECT, "some_unknown_field": "value"}
    path = _write_project(tmp_path, data)

    report = load_project_config(path)

    assert report.is_valid
    assert any("some_unknown_field" in warning for warning in report.warnings)


def test_llm_validation_errors_never_leak_env_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value")
    data = {**VALID_PROJECT, "llm": {"provider": "mock", "model": "mock-v1", "timeout_seconds": -5}}
    path = _write_project(tmp_path, data)

    report = load_project_config(path)

    assert not report.is_valid
    for issue in report.errors:
        assert "sk-super-secret-value" not in issue.message
