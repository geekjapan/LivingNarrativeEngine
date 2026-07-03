import yaml
from typer.testing import CliRunner

from living_narrative.cli import app

runner = CliRunner()


def test_turn_prints_narration_and_status_line_with_exit_zero(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["turn", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "turn 1: applied" in result.output


def test_turn_blocks_when_previous_turn_is_unresolved(tmp_path, build_project):
    project_path = build_project(tmp_path)
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump({"status": "pending_review"}), encoding="utf-8"
    )

    result = runner.invoke(app, ["turn", "--project", str(project_path)])

    assert result.exit_code != 0
    assert "review" in result.output


def test_turn_free_text_intervention_is_recorded(tmp_path, build_project):
    project_path = build_project(tmp_path)

    # --as god: the mock interpreter's random per-seed intervention `type` must never be
    # permission-rejected here, since this test asserts recording, not permission handling
    # (which is covered elsewhere) — god allows every intervention type unconditionally.
    result = runner.invoke(
        app,
        [
            "turn",
            "--project",
            str(project_path),
            "--intervention",
            "ここで停電を起こす",
            "--as",
            "god",
        ],
    )

    assert result.exit_code == 0, result.output
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    intervention_data = yaml.safe_load((turn_dir / "intervention.yaml").read_text(encoding="utf-8"))
    assert len(intervention_data["interventions"]) >= 1


def test_turn_direct_input_records_verbatim_content_without_llm(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(
        app,
        [
            "turn",
            "--project",
            str(project_path),
            "--type",
            "character_directive",
            "--target",
            "char_001",
            "--content",
            "物音に気づいて振り返る",
        ],
    )

    assert result.exit_code == 0, result.output
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    intervention_data = yaml.safe_load((turn_dir / "intervention.yaml").read_text(encoding="utf-8"))
    interventions = intervention_data["interventions"]
    assert len(interventions) == 1
    assert interventions[0]["content"] == "物音に気づいて振り返る"
    assert interventions[0]["type"] == "character_directive"
    assert interventions[0]["target"]["id"] == "char_001"


def test_turn_rejects_intervention_and_type_together(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(
        app,
        [
            "turn",
            "--project",
            str(project_path),
            "--intervention",
            "何か起こす",
            "--type",
            "character_directive",
            "--target",
            "char_001",
            "--content",
            "x",
        ],
    )

    assert result.exit_code == 2


def test_turn_as_god_runs_then_restores_original_user_mode(tmp_path, build_project):
    project_path = build_project(tmp_path)
    original = project_path.read_text(encoding="utf-8")
    assert yaml.safe_load(original)["user_mode"] == "assistant_gm"

    result = runner.invoke(
        app,
        [
            "turn",
            "--project",
            str(project_path),
            "--as",
            "god",
            "--type",
            "canon_edit",
            "--target",
            "canon_099",
            "--content",
            "新しい事実",
        ],
    )

    assert result.exit_code == 0, result.output
    assert project_path.read_text(encoding="utf-8") == original


def test_turn_as_player_character_is_rejected(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(
        app, ["turn", "--project", str(project_path), "--as", "player_character"]
    )

    assert result.exit_code == 2
