import yaml
from typer.testing import CliRunner

from living_narrative.cli import app

runner = CliRunner()


def test_init_creates_project_with_minimal_template_by_default(tmp_path):
    output = tmp_path / "mist_station"

    result = runner.invoke(app, ["init", "--title", "霧の駅", "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert (output / "project.yaml").exists()
    data = yaml.safe_load((output / "project.yaml").read_text(encoding="utf-8"))
    assert data["title"] == "霧の駅"
    assert data["llm"]["provider"] == "mock"


def test_init_mist_station_template_generates_four_characters(tmp_path):
    output = tmp_path / "mist_station"

    result = runner.invoke(
        app,
        [
            "init",
            "--title",
            "霧の駅",
            "--genre",
            "mystery_fantasy",
            "--tone",
            "quiet_ominous",
            "--template",
            "mist_station",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    characters_dir = output / "workspace" / "state" / "characters"
    assert len(list(characters_dir.glob("*.yaml"))) == 4
    gm_vault = yaml.safe_load(
        (output / "workspace" / "state" / "gm_vault.yaml").read_text(encoding="utf-8")
    )
    assert len(gm_vault) == 3
    assert (output / "workspace" / "state" / "scenes" / "scene_001.yaml").exists()


def test_init_unknown_template_exits_2_without_fallback(tmp_path):
    output = tmp_path / "proj"

    result = runner.invoke(
        app,
        ["init", "--title", "x", "--template", "unknown_template", "--output", str(output)],
    )

    assert result.exit_code == 2
    assert not output.exists()


def test_init_rejects_non_empty_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "file.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["init", "--title", "anything", "--output", str(output)])

    assert result.exit_code != 0
