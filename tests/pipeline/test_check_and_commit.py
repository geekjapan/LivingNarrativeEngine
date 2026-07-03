import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.pipeline.models import CheckResult


def _error_check(context, narration_text, resolved_events, diff_candidate):
    return [CheckResult(severity="error", message="boom")]


def test_check_error_stops_for_review_regardless_of_commit_mode(tmp_path, build_project):
    project_path = build_project(tmp_path)
    registry = default_registry()
    registry.register("check", _error_check)

    result = TurnPipeline(registry=registry).run(project_path, commit_mode="auto")

    assert result.status == TurnStatus.STOPPED_FOR_REVIEW
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    assert state_diff["applied"] is False


def test_commit_mode_auto_applies_and_review_defers(tmp_path, build_project):
    project_auto = build_project(tmp_path / "auto")
    project_review = build_project(tmp_path / "review")

    result_auto = TurnPipeline().run(project_auto, commit_mode="auto")
    result_review = TurnPipeline().run(project_review, commit_mode="review")

    assert result_auto.status == TurnStatus.APPLIED
    assert result_review.status == TurnStatus.PENDING_REVIEW

    diff_auto = yaml.safe_load(
        (result_auto.turn_dir / "state_diff.yaml").read_text(encoding="utf-8")
    )
    diff_review = yaml.safe_load(
        (result_review.turn_dir / "state_diff.yaml").read_text(encoding="utf-8")
    )
    assert diff_auto["applied"] is True
    assert diff_review["applied"] is False
