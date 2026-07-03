import json

from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline

runner = CliRunner()


def test_status_human_readable_before_any_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["status", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "ターン: 0" in result.output
    assert "user_mode: assistant_gm" in result.output
    assert "autonomy_level: manual" in result.output
    assert "gm_vault" not in result.output.lower()


def test_status_json_has_required_keys(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    for key in ("current_turn", "pending_review", "user_mode", "autonomy_level"):
        assert key in data
    assert data["current_turn"] == 1
    assert data["pending_review"] is False


def test_status_never_leaks_gm_vault_or_secrets(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        hidden_facts=[
            {"id": "fact_001", "text": "a deep secret", "visibility": "gm_only", "known_by": []}
        ],
    )

    result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    assert "a deep secret" not in result.output


def test_status_exits_2_for_missing_project(tmp_path):
    result = runner.invoke(
        app, ["status", "--project", str(tmp_path / "does_not_exist" / "project.yaml")]
    )

    assert result.exit_code == 2
