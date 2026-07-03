import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus
from living_narrative.session.god import apply_god_edit
from living_narrative.session.loop import run_auto_loop
from living_narrative.session.rerun import discard_for_rerun, rerun_rng_offset
from living_narrative.session.resume import restore_resume_state
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Visibility
from living_narrative.state.store import StateStore


def _write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_resume_presents_pending_review_first_and_ignores_discarded_last_turn(tmp_path):
    runs = tmp_path / "runs"
    _write_yaml(runs / "turn_0017" / "meta.yaml", {"status": "applied", "rng_draws_consumed": 4})
    _write_yaml(
        runs / "turn_0018_discarded_1" / "meta.yaml",
        {"status": "applied", "rng_draws_consumed": 5},
    )
    _write_yaml(
        runs / "turn_0018" / "meta.yaml",
        {"status": "pending_review", "rng_draws_consumed": 2},
    )

    state = restore_resume_state(runs, tmp_path / "interventions.yaml")

    assert state.last_applied_turn == 17
    assert state.pending_review_turn == 18
    assert state.should_present_pending_review_first is True
    assert state.rng_draws_consumed == 11


def test_resume_restores_next_ids_from_discarded_attempts_and_history(tmp_path):
    runs = tmp_path / "runs"
    _write_yaml(runs / "turn_0017" / "events.yaml", [{"id": "event_0081"}])
    _write_yaml(runs / "turn_0018_discarded_1" / "rolls.yaml", [{"id": "roll_0045"}])
    _write_yaml(
        runs / "turn_0018" / "state_diff.yaml",
        {"diff": {"id": "diff_0033", "turn": 18, "changes": []}},
    )
    _write_yaml(tmp_path / "interventions.yaml", {"entries": [{"id": "int_0042"}]})

    state = restore_resume_state(runs, tmp_path / "interventions.yaml")

    assert state.next_ids == {
        "event": "event_0082",
        "diff": "diff_0034",
        "roll": "roll_0046",
        "int": "int_0043",
    }


def test_rerun_offsets_default_and_replay_same_seed(tmp_path):
    runs = tmp_path / "runs"
    _write_yaml(runs / "turn_0017" / "meta.yaml", {"rng_draws_consumed": 40})
    _write_yaml(runs / "turn_0018_discarded_1" / "meta.yaml", {"rng_draws_consumed": 5})

    assert rerun_rng_offset(runs, 18, replay_same_seed=False) == 45
    assert rerun_rng_offset(runs, 18, replay_same_seed=True) == 40


def test_discard_for_rerun_marks_interventions_superseded(tmp_path):
    turn_dir = tmp_path / "runs" / "turn_0018"
    _write_yaml(
        turn_dir / "events.yaml",
        [{"id": "event_0001", "turn": 18, "type": "x", "text": "x", "visibility": "canon"}],
    )
    history = tmp_path / "interventions.yaml"
    _write_yaml(
        history,
        {
            "entries": [
                {
                    "id": "int_0001",
                    "turn": 18,
                    "type": "x",
                    "source_event_ids": ["event_0001"],
                }
            ]
        },
    )

    discarded = discard_for_rerun(turn_dir, history)

    assert discarded.name == "turn_0018_discarded_1"
    data = yaml.safe_load(history.read_text(encoding="utf-8"))
    assert data["entries"][0]["superseded_by_rerun"] is True


def test_god_edit_records_diff_and_auto_review(tmp_path, build_project):
    project_path = build_project(tmp_path)
    workspace = project_path.parent / "workspace"
    turn_dir = workspace / "runs" / "turn_0001"
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="world",
                op="set",
                path="summary",
                value="god edit",
                visibility=Visibility.CANON,
            )
        ],
    )

    bundle = apply_god_edit(StateStore.load(workspace / "state"), diff, turn_dir)

    assert bundle.world.summary == "god edit"
    review = yaml.safe_load((turn_dir / "review.yaml").read_text(encoding="utf-8"))
    assert review["auto_applied"] is True


def test_auto_loop_stops_when_pipeline_returns_review(tmp_path, build_project):
    project_path = build_project(tmp_path)

    class OneReviewPipeline(TurnPipeline):
        def run(self, project_path, **kwargs):
            return type("Result", (), {"turn": 1, "status": TurnStatus.STOPPED_FOR_REVIEW})()

    result = run_auto_loop(project_path, 5, pipeline=OneReviewPipeline())

    assert len(result.turns) == 1
    assert result.turns[0].status == TurnStatus.STOPPED_FOR_REVIEW
