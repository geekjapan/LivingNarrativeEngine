import json

from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline

runner = CliRunner()


def test_metrics_human_readable_before_any_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["metrics", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "turns: 0" in result.output
    assert "emotions:" in result.output
    assert "memory: summary件数=0" in result.output


def test_metrics_json_round_trips_after_a_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["metrics", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["turns"]["total"] == 1
    assert data["turns"]["by_status"] == {"applied": 1}
    for key in ("turns", "emotions", "pacing", "threads", "threats", "scenes", "checks", "memory"):
        assert key in data


def test_metrics_exits_2_for_missing_project(tmp_path):
    result = runner.invoke(
        app, ["metrics", "--project", str(tmp_path / "does_not_exist" / "project.yaml")]
    )

    assert result.exit_code == 2
