import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline

runner = CliRunner()


def _write_pending_turn(project_path, *, changes):
    runs_dir = project_path.parent / "workspace" / "runs"
    turn_dir = runs_dir / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump({"status": "pending_review", "rng_draws_consumed": 0}), encoding="utf-8"
    )
    (turn_dir / "state_diff.yaml").write_text(
        yaml.safe_dump(
            {
                "diff": {"id": "diff_0001", "turn": 1, "changes": changes},
                "rejected_changes": [],
                "applied": False,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return turn_dir


_TWO_CHANGES = [
    {
        "target": "world",
        "op": "set",
        "path": "summary",
        "value": "edited summary",
        "visibility": "canon",
    },
    {"target": "world", "op": "set", "path": "name", "value": "edited name", "visibility": "canon"},
]


def test_review_reports_no_pending_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)  # applied, nothing pending

    result = runner.invoke(app, ["review", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "レビュー対象のターンはありません" in result.output


def test_review_accept_all_applies_the_diff(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(
        app, ["review", "--project", str(project_path), "--decision", "accept_all"]
    )

    assert result.exit_code == 0, result.output
    world = yaml.safe_load(
        (project_path.parent / "workspace" / "state" / "world.yaml").read_text(encoding="utf-8")
    )
    assert world["summary"] == "edited summary"
    assert world["name"] == "edited name"
    meta = yaml.safe_load(
        (project_path.parent / "workspace" / "runs" / "turn_0001" / "meta.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert meta["status"] == "applied"


def test_review_partial_applies_only_selected_indices(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(
        app,
        ["review", "--project", str(project_path), "--decision", "partial", "--apply", "0"],
    )

    assert result.exit_code == 0, result.output
    world = yaml.safe_load(
        (project_path.parent / "workspace" / "state" / "world.yaml").read_text(encoding="utf-8")
    )
    assert world["summary"] == "edited summary"
    assert world["name"] != "edited name"
    review = yaml.safe_load(
        (project_path.parent / "workspace" / "runs" / "turn_0001" / "review.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert review["applied_change_indices"] == [0]


def test_review_reject_all_leaves_state_unchanged(tmp_path, build_project):
    project_path = build_project(tmp_path)
    original_world = (project_path.parent / "workspace" / "state" / "world.yaml").read_text(
        encoding="utf-8"
    )
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(
        app, ["review", "--project", str(project_path), "--decision", "reject_all"]
    )

    assert result.exit_code == 0, result.output
    assert (project_path.parent / "workspace" / "state" / "world.yaml").read_text(
        encoding="utf-8"
    ) == original_world


def test_review_partial_requires_apply(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(app, ["review", "--project", str(project_path), "--decision", "partial"])

    assert result.exit_code == 2


def test_review_edit_requires_patch(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(app, ["review", "--project", str(project_path), "--decision", "edit"])

    assert result.exit_code == 2


def test_review_replay_same_seed_without_rerun_turn_is_an_error(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(
        app,
        [
            "review",
            "--project",
            str(project_path),
            "--decision",
            "accept_all",
            "--replay-same-seed",
        ],
    )

    assert result.exit_code == 2


def test_review_without_decision_and_no_tty_is_an_error(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(app, ["review", "--project", str(project_path)])

    assert result.exit_code == 2


def test_review_rerun_turn_discards_and_reruns(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_pending_turn(project_path, changes=_TWO_CHANGES)

    result = runner.invoke(
        app, ["review", "--project", str(project_path), "--decision", "rerun_turn"]
    )

    assert result.exit_code == 0, result.output
    runs_dir = project_path.parent / "workspace" / "runs"
    assert (runs_dir / "turn_0001_discarded_1").is_dir()
    assert (runs_dir / "turn_0001" / "narration.md").exists()
    assert "turn 1:" in result.output
