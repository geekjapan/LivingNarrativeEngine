import importlib
import json

import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Visibility
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import RecoveryState, commit_state_diff, state_hash

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
    assert "cannot be cleared safely" in result.output
    assert "living-narrative restore <backup-root>" in result.output


def test_doctor_repair_help_does_not_claim_to_clear_quarantine():
    result = runner.invoke(app, ["doctor", "--help"])

    assert result.exit_code == 0, result.output
    assert "--clear-quarantine" not in result.output


def test_doctor_repair_keeps_discarded_turn_audit_fields(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    before = StateStore.load(state_dir)
    commit_state_diff(before, _diff(), state_dir, turn_dir)
    StateStore.save(before, state_dir)
    intent = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    intent["state_hash_before"] = state_hash(state_dir)
    (turn_dir / "commit_intent.yaml").write_text(
        yaml.safe_dump(intent, sort_keys=False), encoding="utf-8"
    )

    result = runner.invoke(app, ["doctor", "--project", str(project_path), "--repair", "--json"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["state"] == "clean"
    assert report["turn"] == "turn_0001"
    assert report["turn_dir"] == str(turn_dir)

    discarded = list(turn_dir.parent.glob("turn_0001_discarded_*"))
    assert len(discarded) == 1
    discarded_intent = yaml.safe_load(
        (discarded[0] / "commit_intent.yaml").read_text(encoding="utf-8")
    )
    assert discarded_intent["state_hash_before"] == intent["state_hash_before"]
    assert discarded_intent["state_hash_after"] == intent["state_hash_after"]


def test_doctor_repair_reports_legacy_applied_turn_preserved(tmp_path, build_project):
    project_path = build_project(tmp_path)
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(yaml.safe_dump({"status": "applied"}), encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--project", str(project_path), "--repair", "--json"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["state"] == "discard"
    assert report["action"] == "no action needed (legacy applied turn preserved)"
    assert turn_dir.exists()


def test_doctor_repair_reports_io_errors_without_traceback(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path)
    doctor_module = importlib.import_module("living_narrative.cli.doctor")

    def fail_classification(*_args, **_kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(doctor_module, "classify_recovery_state", fail_classification)
    result = runner.invoke(app, ["doctor", "--project", str(project_path), "--repair"])

    assert result.exit_code == 1
    assert "permission denied" in result.output
    assert "Traceback" not in result.output


def test_doctor_repair_trusts_post_repair_diagnosis(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path)
    doctor_module = importlib.import_module("living_narrative.cli.doctor")
    calls = 0

    def classify(_turn_dir, _state_dir, *, apply=True):
        nonlocal calls
        calls += 1
        return RecoveryState.DISCARD if calls == 1 else RecoveryState.QUARANTINE

    monkeypatch.setattr(doctor_module, "classify_recovery_state", classify)
    result = runner.invoke(app, ["doctor", "--project", str(project_path), "--repair", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["state"] == "quarantine"
