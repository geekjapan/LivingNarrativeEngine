import pytest
import yaml

from living_narrative.workspace.init import InitDestinationExistsError, create_project
from living_narrative.workspace.layout import (
    MINIMAL_STATE_CONTENT,
    OPTIONAL_STATE_FILES,
    REQUIRED_STATE_FILES,
    STATE_SUBDIRS,
)


def test_creates_project_yaml_and_workspace_layout(tmp_path):
    output = tmp_path / "mist_station"

    project_path = create_project(output, title="霧の駅")

    assert project_path == output / "project.yaml"
    data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert data["title"] == "霧の駅"
    assert data["llm"]["provider"] == "mock"
    assert data["autonomy_level"] == "manual"
    assert data["user_mode"] == "assistant_gm"
    assert "llm_profiles" not in data
    assert "llm_bindings" not in data

    state_dir = output / "workspace" / "state"
    for filename in (*REQUIRED_STATE_FILES, *OPTIONAL_STATE_FILES):
        assert (state_dir / filename).is_file(), filename
    for subdir in STATE_SUBDIRS:
        assert (state_dir / subdir).is_dir()
    assert (output / "workspace" / "runs").is_dir()
    assert (output / "workspace" / "exports").is_dir()
    assert MINIMAL_STATE_CONTENT  # sanity: template is non-empty


def test_slug_generated_from_ascii_title(tmp_path):
    project_path = create_project(tmp_path / "proj", title="Mist Station!")
    data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert data["id"] == "mist-station"


def test_slug_falls_back_to_project_for_non_ascii_title(tmp_path):
    project_path = create_project(tmp_path / "proj", title="霧の駅")
    data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert data["id"] == "project"


def test_refuses_to_overwrite_non_empty_directory(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "some_file.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(InitDestinationExistsError):
        create_project(output, title="anything")

    assert (output / "some_file.txt").read_text(encoding="utf-8") == "keep me"
    assert not (output / "project.yaml").exists()


def test_allows_init_into_existing_empty_directory(tmp_path):
    output = tmp_path / "empty_dir"
    output.mkdir()

    project_path = create_project(output, title="Empty Dir Project")

    assert project_path.exists()
