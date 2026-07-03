from typer.testing import CliRunner

from living_narrative.cli import app

runner = CliRunner()


def test_init_command_creates_project(tmp_path):
    output = tmp_path / "mist_station"

    result = runner.invoke(app, [str(output), "--title", "霧の駅"])

    assert result.exit_code == 0, result.output
    assert (output / "project.yaml").exists()


def test_init_command_rejects_non_empty_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "file.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, [str(output), "--title", "anything"])

    assert result.exit_code != 0
