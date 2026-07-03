import pytest
import yaml

from living_narrative.state.store import StateStore
from living_narrative.templates.registry import UnknownTemplateError
from living_narrative.workspace.init import InitDestinationExistsError, create_project
from living_narrative.workspace.layout import (
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
    StateStore.load(state_dir)  # sanity: minimal template is schema-valid, not just present


def test_genre_and_tone_flow_into_project_yaml(tmp_path):
    project_path = create_project(
        tmp_path / "proj", title="Test", genre="mystery_fantasy", tone="quiet_ominous"
    )
    data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert data["genre"] == "mystery_fantasy"
    assert data["tone"] == "quiet_ominous"


def test_mist_station_template_generates_four_characters_and_gm_vault(tmp_path):
    output = tmp_path / "mist_station"

    create_project(output, title="霧の駅", template="mist_station")

    state_dir = output / "workspace" / "state"
    bundle = StateStore.load(state_dir)
    assert len(bundle.characters) == 4
    assert len(bundle.gm_vault) == 3
    assert any(scene.id == "scene_001" for scene in bundle.scenes)


def test_unknown_template_name_raises_and_creates_nothing(tmp_path):
    output = tmp_path / "proj"

    with pytest.raises(UnknownTemplateError):
        create_project(output, title="anything", template="unknown_template")

    assert not output.exists()


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
