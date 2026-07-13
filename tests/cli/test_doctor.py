import json

import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Visibility
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import commit_state_diff

runner = CliRunner()


def _diff() -> StateDiff:
    return StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="world",
                op="set",
                path="summary",
                value="committed",
                visibility=Visibility.CANON,
            )
        ],
    )


def test_doctor_reports_clean_project_as_json(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["doctor", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["state"] == "clean"


def test_doctor_repairs_missing_meta(tmp_path, build_project):
    project_path = build_project(tmp_path)
    turn = TurnPipeline().run(project_path)
    turn_meta = turn.turn_dir / "meta.yaml"
    turn_meta.unlink()

    result = runner.invoke(app, ["doctor", "--project", str(project_path), "--repair"])

    assert result.exit_code == 0, result.output
    assert "completed meta.yaml" in result.output
    assert yaml.safe_load(turn_meta.read_text(encoding="utf-8"))["status"] == "applied"


def test_doctor_quarantine_guides_backup_restore(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    commit_state_diff(StateStore.load(state_dir), _diff(), state_dir, turn_dir)
    intent = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    intent["state_hash_after"] = "not-the-live-state"
    (turn_dir / "commit_intent.yaml").write_text(
        yaml.safe_dump(intent, sort_keys=False), encoding="utf-8"
    )

    result = runner.invoke(app, ["doctor", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "quarantine" in result.output
    assert "living-narrative restore <backup-root>" in result.output
