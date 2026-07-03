from pathlib import Path

from living_narrative.workspace.init import create_project
from living_narrative.workspace.loader import load_project, resolve_workspace_paths


def test_relative_workspace_paths_resolve_against_project_yaml_dir(tmp_path):
    project_dir = tmp_path / "projects" / "mist_station"
    project_path = create_project(project_dir, title="Mist Station")

    result = load_project(project_path)

    assert result.is_valid
    assert result.paths.state == project_dir / "workspace" / "state"
    assert result.paths.runs == project_dir / "workspace" / "runs"
    assert result.paths.exports == project_dir / "workspace" / "exports"
    assert result.missing_state_files == []


def test_missing_required_state_file_is_reported(tmp_path):
    project_dir = tmp_path / "mist_station"
    project_path = create_project(project_dir, title="Mist Station")
    (project_dir / "workspace" / "state" / "gm_vault.yaml").unlink()

    result = load_project(project_path)

    assert not result.is_valid
    assert "gm_vault.yaml" in result.missing_state_files


def test_resolve_workspace_paths_relative_example():
    from living_narrative.state.models import WorkspaceConfig

    project_path = Path("projects/mist_station/project.yaml")
    workspace = WorkspaceConfig(
        root="workspace",
        state="workspace/state",
        runs="workspace/runs",
        exports="workspace/exports",
    )

    paths = resolve_workspace_paths(project_path, workspace)

    assert paths.state == Path("projects/mist_station/workspace/state")
