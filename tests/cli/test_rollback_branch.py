"""``living-narrative rollback``/``branch`` (cli/spec.md; Issue 018): rewind project state
using saved inverse diffs, and copy-then-rewind for branches."""

import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline, TurnStatus
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project

runner = CliRunner()


def _runs_dir(project_path):
    return project_path.parent / "workspace" / "runs"


def _run_turns(project_path, n):
    pipeline = TurnPipeline()
    for _ in range(n):
        result = pipeline.run(project_path)
        assert result.status == TurnStatus.APPLIED, result


def _write_pending_turn(project_path, turn_number):
    turn_dir = _runs_dir(project_path) / f"turn_{turn_number:04d}"
    turn_dir.mkdir(parents=True, exist_ok=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump({"status": "pending_review", "rng_draws_consumed": 0}), encoding="utf-8"
    )
    (turn_dir / "state_diff.yaml").write_text(
        yaml.safe_dump(
            {
                "diff": {"id": f"diff_{turn_number:04d}", "turn": turn_number, "changes": []},
                "rejected_changes": [],
                "applied": False,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def test_rollback_restores_state_and_timeline(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 3)
    paths = load_project(project_path).paths
    snapshot = StateStore.load(paths.state).model_dump(mode="json")
    _run_turns(project_path, 2)  # now at turn 5

    result = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "3", "--yes"]
    )

    assert result.exit_code == 0, result.output
    restored = StateStore.load(paths.state).model_dump(mode="json")
    assert restored == snapshot
    assert len(restored["timeline"]) == len(snapshot["timeline"])

    runs_dir = _runs_dir(project_path)
    for n in (1, 2, 3):
        assert (runs_dir / f"turn_{n:04d}").is_dir()
    assert (runs_dir / "turn_0004_rolledback_1").is_dir()
    assert (runs_dir / "turn_0005_rolledback_1").is_dir()
    assert not (runs_dir / "turn_0004").exists()
    assert not (runs_dir / "turn_0005").exists()


def test_rollback_then_next_turn_renumbers_and_rng_accounting_survives(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 5)

    result = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "3", "--yes"]
    )
    assert result.exit_code == 0, result.output

    next_result = TurnPipeline().run(project_path)
    assert next_result.turn == 4
    assert next_result.status == TurnStatus.APPLIED


def test_rollback_rejects_to_turn_at_or_above_current(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 3)

    at_current = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "3", "--yes"]
    )
    assert at_current.exit_code == 2

    above_current = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "5", "--yes"]
    )
    assert above_current.exit_code == 2


def test_rollback_rejects_missing_inverse_diff(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 5)
    (_runs_dir(project_path) / "turn_0004" / "inverse_diff.yaml").unlink()

    result = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "2", "--yes"]
    )

    assert result.exit_code == 2
    assert "inverse_diff" in result.output


def test_rollback_rejects_pending_review_latest_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 3)
    _write_pending_turn(project_path, turn_number=4)

    result = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "2", "--yes"]
    )

    assert result.exit_code == 2
    assert "review" in result.output


def test_rollback_prompts_and_aborts_without_yes(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 3)

    result = runner.invoke(
        app, ["rollback", "--project", str(project_path), "--to-turn", "1"], input="n\n"
    )

    assert result.exit_code == 0, result.output
    assert "Aborted" in result.output
    assert (_runs_dir(project_path) / "turn_0002").is_dir()


def test_branch_copies_and_rewinds_independently(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 3)
    paths = load_project(project_path).paths
    snapshot = StateStore.load(paths.state).model_dump(mode="json")
    _run_turns(project_path, 2)  # original now at turn 5

    branch_dir = tmp_path / "branch_a"
    result = runner.invoke(
        app,
        [
            "branch",
            "--project",
            str(project_path),
            "--from-turn",
            "3",
            "--output",
            str(branch_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    branch_project_path = branch_dir / "project.yaml"
    branch_title = yaml.safe_load(branch_project_path.read_text(encoding="utf-8"))["title"]
    assert branch_title.endswith("(branch@3)")

    branch_paths = load_project(branch_project_path).paths
    branch_state = StateStore.load(branch_paths.state).model_dump(mode="json")
    assert branch_state == snapshot

    original_state = StateStore.load(paths.state).model_dump(mode="json")
    assert original_state != snapshot  # original kept going, diverged from the turn-3 snapshot
    original_runs = _runs_dir(project_path)
    assert (original_runs / "turn_0005").is_dir()
    assert not any(original_runs.glob("*_rolledback_*"))

    branch_result = TurnPipeline().run(branch_project_path)
    assert branch_result.turn == 4
    assert not (original_runs / "turn_0006").exists()


def test_branch_rejects_existing_output_dir(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _run_turns(project_path, 3)
    existing = tmp_path / "already_here"
    existing.mkdir()

    result = runner.invoke(
        app,
        [
            "branch",
            "--project",
            str(project_path),
            "--from-turn",
            "1",
            "--output",
            str(existing),
        ],
    )

    assert result.exit_code == 2
