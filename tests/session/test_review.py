import yaml

from living_narrative.session.review import ReviewDecision, resolve_review, write_artifact_diff
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Visibility
from living_narrative.state.store import StateStore


def _change(value: str, source_event: str = "event_0001"):
    return StateDiffChange(
        target="world",
        op="set",
        path="summary",
        value=value,
        visibility=Visibility.CANON,
        source_event=source_event,
    )


def _pending_turn(project_path, turn_dir, diff):
    turn_dir.mkdir(parents=True)
    write_artifact_diff(turn_dir, diff, applied=False)
    (turn_dir / "events.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "event_0001",
                    "turn": 1,
                    "type": "world_directive",
                    "cause": "intervention:int_0001",
                    "text": "changed",
                    "visibility": "canon",
                }
            ]
        ),
        encoding="utf-8",
    )
    (turn_dir / "intervention.yaml").write_text(
        yaml.safe_dump(
            {
                "turn": 1,
                "interventions": [
                    {
                        "id": "int_0001",
                        "turn": 1,
                        "type": "world_directive",
                        "target": {"kind": "world"},
                        "content": "change",
                        "visibility": "canon",
                        "user_role": "assistant_gm",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump({"turn": 1, "status": "pending_review"}),
        encoding="utf-8",
    )
    return project_path.parent / "workspace"


def test_partial_review_applies_selected_changes_and_records_review(tmp_path, build_project):
    project_path = build_project(tmp_path)
    workspace = project_path.parent / "workspace"
    turn_dir = workspace / "runs" / "turn_0001"
    diff = StateDiff(id="diff_0001", turn=1, changes=[_change("one"), _change("two")])
    _pending_turn(project_path, turn_dir, diff)

    result = resolve_review(
        workspace_root=workspace,
        state_dir=workspace / "state",
        turn_dir=turn_dir,
        decision=ReviewDecision.PARTIAL,
        decided_by="assistant_gm",
        selected_change_indices={0},
    )

    assert result.resulting_turn_status == "applied"
    assert (turn_dir / "state_diff_pre_review.yaml").exists()
    assert StateStore.load(workspace / "state").world.summary == "one"
    review = yaml.safe_load((turn_dir / "review.yaml").read_text(encoding="utf-8"))
    assert review["applied_change_indices"] == [0]


def test_edit_review_validates_and_applies_edited_diff(tmp_path, build_project):
    project_path = build_project(tmp_path)
    workspace = project_path.parent / "workspace"
    turn_dir = workspace / "runs" / "turn_0001"
    _pending_turn(
        project_path,
        turn_dir,
        StateDiff(id="diff_0001", turn=1, changes=[_change("old")]),
    )

    resolve_review(
        workspace_root=workspace,
        state_dir=workspace / "state",
        turn_dir=turn_dir,
        decision="edit",
        decided_by="assistant_gm",
        edited_diff=StateDiff(id="diff_0001", turn=1, changes=[_change("edited")]),
    )

    assert StateStore.load(workspace / "state").world.summary == "edited"
    assert (turn_dir / "inverse_diff.yaml").exists()


def test_reject_all_records_applied_nothing_history_once(tmp_path, build_project):
    project_path = build_project(tmp_path)
    workspace = project_path.parent / "workspace"
    turn_dir = workspace / "runs" / "turn_0001"
    _pending_turn(project_path, turn_dir, StateDiff(id="diff_0001", turn=1, changes=[_change("x")]))

    resolve_review(
        workspace_root=workspace,
        state_dir=workspace / "state",
        turn_dir=turn_dir,
        decision="reject_all",
        decided_by="assistant_gm",
    )
    resolve_review(
        workspace_root=workspace,
        state_dir=workspace / "state",
        turn_dir=turn_dir,
        decision="reject_all",
        decided_by="assistant_gm",
    )

    history = yaml.safe_load((workspace / "interventions.yaml").read_text(encoding="utf-8"))
    assert len(history["entries"]) == 1
    assert history["entries"][0]["applied_nothing"] is True
    assert (
        yaml.safe_load((turn_dir / "review.yaml").read_text(encoding="utf-8"))["decision"]
        == "reject_all"
    )
