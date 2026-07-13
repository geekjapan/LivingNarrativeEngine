import pytest
import yaml

from living_narrative.pipeline import (
    TurnPipeline,
    TurnStatus,
    UnresolvedTurnError,
    default_registry,
    total_rng_draws_consumed,
)
from living_narrative.state.transaction import RecoveryError


def test_pending_review_turn_blocks_next_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path, commit_mode="review")

    with pytest.raises(UnresolvedTurnError):
        TurnPipeline().run(project_path)


def test_applied_turn_advances_to_next_number(tmp_path, build_project):
    project_path = build_project(tmp_path)
    first = TurnPipeline().run(project_path)
    second = TurnPipeline().run(project_path)

    assert first.turn == 1
    assert second.turn == 2
    assert first.status == TurnStatus.APPLIED
    assert second.status == TurnStatus.APPLIED


def test_missing_meta_yaml_blocks_next_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    first = TurnPipeline().run(project_path)
    (first.turn_dir / "meta.yaml").unlink()

    with pytest.raises(UnresolvedTurnError):
        TurnPipeline().run(project_path)


def test_quarantined_latest_turn_blocks_pipeline_mutation(tmp_path, build_project):
    project_path = build_project(tmp_path)
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "commit_intent.yaml").write_text("invalid: [", encoding="utf-8")

    with pytest.raises(RecoveryError, match="quarantine"):
        TurnPipeline().run(project_path)


def test_failed_turn_is_retried_at_same_number_with_discarded_dir_and_rng_accounting(
    tmp_path, build_project
):
    project_path = build_project(tmp_path)
    attempts = {"count": 0}

    def flaky_resolve(context, world_events, action_candidates, allocate_event_id, record_roll):
        roll = context.random_engine.roll_dice("1d6", turn=context.turn)
        record_roll(roll)
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient failure")
        return []

    registry = default_registry()
    registry.register("resolve", flaky_resolve)

    first = TurnPipeline(registry=registry).run(project_path)
    assert first.status == TurnStatus.FAILED
    assert first.turn == 1

    second = TurnPipeline(registry=registry).run(project_path)
    assert second.status == TurnStatus.APPLIED
    assert second.turn == 1
    assert second.turn_dir == first.turn_dir

    discarded_dir = second.turn_dir.parent / "turn_0001_discarded_1"
    assert discarded_dir.exists()

    discarded_meta = yaml.safe_load((discarded_dir / "meta.yaml").read_text(encoding="utf-8"))
    second_meta = yaml.safe_load((second.turn_dir / "meta.yaml").read_text(encoding="utf-8"))

    assert discarded_meta["rng_draws_consumed"] == 2
    assert second_meta["rng_draws_consumed"] == 2

    assert total_rng_draws_consumed(second.turn_dir.parent) == 4
