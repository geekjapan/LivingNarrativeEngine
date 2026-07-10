from pathlib import Path

import pytest
import yaml

from living_narrative.state.validation import load_project_config
from living_narrative.workspace.init import create_project
from living_narrative.workspace.migrations import CURRENT_SCHEMA_VERSION


def _write_project(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _project_data() -> dict:
    return {
        "schema_version": 1,
        "id": "migration-test",
        "title": "移行テスト",
        "genre": "mystery",
        "tone": "quiet",
        "autonomy_level": "manual",
        "user_mode": "assistant_gm",
        "random_seed": "seed",
        "renderer": "novel",
        "llm": {"provider": "mock", "model": "mock-v1"},
        "workspace": {
            "root": "workspace",
            "state": "workspace/state",
            "runs": "workspace/runs",
            "exports": "workspace/exports",
        },
    }


def test_loader_defaults_legacy_project_to_schema_version_one(tmp_path):
    path = tmp_path / "project.yaml"
    data = _project_data()
    del data["schema_version"]
    _write_project(path, data)

    report = load_project_config(path)

    assert report.is_valid
    assert report.config.schema_version == 1
    assert "schema_version" not in yaml.safe_load(path.read_text(encoding="utf-8"))


def test_loader_rejects_future_schema_version_with_clear_error(tmp_path):
    path = tmp_path / "project.yaml"
    _write_project(path, {**_project_data(), "schema_version": 2})

    report = load_project_config(path)

    assert not report.is_valid
    assert report.errors[0].field == "schema_version"
    assert "newer than supported version 1" in report.errors[0].message


def test_loader_applies_injected_migration_chain_before_validation(tmp_path):
    path = tmp_path / "project.yaml"
    data = _project_data()
    del data["tone"]
    _write_project(path, data)
    migrations = {
        1: lambda raw: {**raw, "schema_version": 2, "genre_and_tone": "mystery/quiet"},
        2: lambda raw: {
            **raw,
            "schema_version": 3,
            "tone": raw["genre_and_tone"].split("/")[1],
        },
    }

    report = load_project_config(path, migrations=migrations, current_schema_version=3)

    assert report.is_valid
    assert report.config.schema_version == 3
    assert report.config.tone == "quiet"
    assert "tone" not in yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("template", ["minimal", "mist_station"])
def test_new_project_writes_current_schema_version_for_every_template(tmp_path, template):
    project_path = create_project(tmp_path / template, title="新規プロジェクト", template=template)

    raw = yaml.safe_load(project_path.read_text(encoding="utf-8"))

    assert raw["schema_version"] == CURRENT_SCHEMA_VERSION
