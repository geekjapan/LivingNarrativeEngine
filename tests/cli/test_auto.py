import yaml
from typer.testing import CliRunner

import living_narrative.cli.auto as auto_module
from living_narrative.cli import app
from living_narrative.pipeline import TurnRunResult, TurnStatus
from living_narrative.session.loop import AutoLoopResult
from living_narrative.state.transaction import RecoveryError

runner = CliRunner()


def test_auto_runs_the_requested_number_of_turns(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["auto", "--project", str(project_path), "--turns", "5"])

    assert result.exit_code == 0, result.output
    runs_dir = project_path.parent / "workspace" / "runs"
    for n in range(1, 6):
        assert (runs_dir / f"turn_{n:04d}").is_dir()


def test_auto_rejects_turns_and_until_together(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(
        app,
        ["auto", "--project", str(project_path), "--turns", "5", "--until", "scene_end"],
    )

    assert result.exit_code == 2


def test_auto_requires_turns_or_until(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["auto", "--project", str(project_path)])

    assert result.exit_code == 2


def test_auto_cli_reports_recovery_error_guidance(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path)

    def fail_run(*_args, **_kwargs):
        raise RecoveryError(
            "cannot mutate project while recovery state is quarantine", quarantine=True
        )

    monkeypatch.setattr(auto_module, "run_auto_loop", fail_run)
    result = runner.invoke(app, ["auto", "--project", str(project_path), "--turns", "1"])

    assert result.exit_code == 1
    assert "restore a backup" in result.output
    assert "Traceback" not in result.output


def _write_turn_dir(runs_dir, turn, *, stop_conditions=()):
    turn_dir = runs_dir / f"turn_{turn:04d}"
    turn_dir.mkdir(parents=True)
    (turn_dir / "narration.md").write_text(
        f"---\nturn: {turn}\nstyle: novel\nvisibility: reader\n---\n\nturn {turn} body\n",
        encoding="utf-8",
    )
    (turn_dir / "agent_io").mkdir()
    (turn_dir / "agent_io" / "stop_conditions.yaml").write_text(
        yaml.safe_dump(list(stop_conditions), allow_unicode=True), encoding="utf-8"
    )
    return turn_dir


def test_auto_until_scene_end_stops_early_and_reports_the_reason(
    tmp_path, build_project, monkeypatch
):
    # The engine's stop-condition evaluation (agent-runtime capability) is what actually
    # detects scene_end; this test only verifies the CLI dispatches --until correctly and
    # surfaces the stop reason, so the collaborator is faked rather than re-driving a real
    # scene transition through the mock agents.
    project_path = build_project(tmp_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    turn_one = _write_turn_dir(runs_dir, 1)
    turn_two = _write_turn_dir(
        runs_dir, 2, stop_conditions=[{"name": "scene_end", "should_stop": True}]
    )
    fake_result = AutoLoopResult(
        turns=[
            TurnRunResult(turn=1, status=TurnStatus.APPLIED, turn_dir=turn_one),
            TurnRunResult(turn=2, status=TurnStatus.STOPPED_FOR_REVIEW, turn_dir=turn_two),
        ]
    )
    captured_turn_count = {}

    def fake_run_auto_loop(project_path_arg, target_turn_count):
        captured_turn_count["value"] = target_turn_count
        return fake_result

    monkeypatch.setattr(auto_module, "run_auto_loop", fake_run_auto_loop)

    result = runner.invoke(app, ["auto", "--project", str(project_path), "--until", "scene_end"])

    assert result.exit_code == 0, result.output
    assert "turn 1: applied" in result.output
    assert "turn 2: stopped_for_review" in result.output
    assert "stopped: scene_end" in result.output
    assert captured_turn_count["value"] == auto_module._UNTIL_SCENE_END_TURN_CAP
