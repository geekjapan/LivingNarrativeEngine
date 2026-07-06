from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline

runner = CliRunner()


def test_export_replay_writes_output_and_creates_parent_dirs(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    output = tmp_path / "out" / "replay.md"

    result = runner.invoke(
        app,
        [
            "export",
            "replay",
            "--project",
            str(project_path),
            "--output",
            str(output),
            "--style",
            "novel",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()


def test_export_replay_errors_when_no_turns_have_run(tmp_path, build_project):
    project_path = build_project(tmp_path)
    output = tmp_path / "replay.md"

    result = runner.invoke(
        app, ["export", "replay", "--project", str(project_path), "--output", str(output)]
    )

    assert result.exit_code == 1
    assert not output.exists()


def test_export_replay_rejects_unknown_style(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    output = tmp_path / "replay.md"

    result = runner.invoke(
        app,
        [
            "export",
            "replay",
            "--project",
            str(project_path),
            "--output",
            str(output),
            "--style",
            "unknown_style",
        ],
    )

    assert result.exit_code == 2


def test_export_scenes_writes_yaml_and_markdown_under_workspace_exports(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "scenes", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    assert (exports_dir / "scenes.yaml").exists()
    assert (exports_dir / "scenes.md").exists()


def test_export_scenes_accepts_gm_flag(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "scenes", "--project", str(project_path), "--gm"])

    assert result.exit_code == 0, result.output


def test_export_scenes_errors_when_project_not_found(tmp_path):
    output = tmp_path / "does_not_exist" / "project.yaml"

    result = runner.invoke(app, ["export", "scenes", "--project", str(output)])

    assert result.exit_code == 2
