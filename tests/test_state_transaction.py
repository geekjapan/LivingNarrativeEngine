import pytest
import yaml

from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Visibility
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import (
    ProjectLockError,
    RecoveryState,
    classify_recovery_state,
    commit_state_diff,
    project_lock,
    state_hash,
)


def _diff(value: str = "committed") -> StateDiff:
    return StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="world",
                op="set",
                path="summary",
                value=value,
                visibility=Visibility.CANON,
            )
        ],
    )


def test_commit_writes_journal_before_state_and_pins_meta(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    before = StateStore.load(state_dir)

    result = commit_state_diff(before, _diff(), state_dir, turn_dir, rng_start_offset=7)

    intent = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    meta = yaml.safe_load((turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert (turn_dir / "inverse_diff.yaml").exists()
    assert intent["diff_id"] == "diff_0001"
    assert intent["rng_start_offset"] == 7
    assert intent["state_hash_before"] != intent["state_hash_after"]
    assert meta["state_hash_before"] == intent["state_hash_before"]
    assert meta["state_hash_after"] == intent["state_hash_after"]
    assert state_hash(state_dir) == intent["state_hash_after"]
    assert StateStore.load(state_dir).world.summary == "committed"
    assert result.inverse_diff.changes
    assert classify_recovery_state(turn_dir, state_dir) is RecoveryState.CLEAN


def test_artifact_failure_cannot_advance_state_without_inverse(
    tmp_path, build_project, monkeypatch
):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    original = StateStore.load(state_dir).model_dump(mode="json")

    import living_narrative.state.transaction as transaction

    monkeypatch.setattr(
        transaction,
        "save_apply_artifacts",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("injected artifact failure")),
    )

    with pytest.raises(RuntimeError, match="injected artifact failure"):
        commit_state_diff(StateStore.load(state_dir), _diff(), state_dir, turn_dir)

    assert StateStore.load(state_dir).model_dump(mode="json") == original
    assert not (turn_dir / "inverse_diff.yaml").exists()


def test_commit_preserves_existing_meta_fields(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "turn": 1,
                "status": "pending_review",
                "pipeline_version": "test-pipeline",
                "custom_meta": {"source": "fixture"},
            }
        ),
        encoding="utf-8",
    )

    commit_state_diff(
        StateStore.load(state_dir),
        _diff(),
        state_dir,
        turn_dir,
        meta={"turn": 1, "commit_mode": "review"},
    )

    meta = yaml.safe_load((turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["pipeline_version"] == "test-pipeline"
    assert meta["custom_meta"] == {"source": "fixture"}
    assert meta["commit_mode"] == "review"
    assert meta["status"] == "applied"


def test_recovery_classifies_hash_after_and_hash_before(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    before_bundle = StateStore.load(state_dir)
    before_hash = state_hash(state_dir)

    commit_state_diff(before_bundle, _diff(), state_dir, turn_dir)
    (turn_dir / "meta.yaml").unlink()
    assert classify_recovery_state(turn_dir, state_dir) is RecoveryState.RECOVER_META

    intent_before = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))[
        "state_hash_before"
    ]
    intent = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    StateStore.save(before_bundle, state_dir)
    intent["state_hash_before"] = state_hash(state_dir)
    (turn_dir / "commit_intent.yaml").write_text(
        yaml.safe_dump(intent, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    assert intent["state_hash_before"] != intent_before
    assert intent["state_hash_before"] != before_hash
    assert classify_recovery_state(turn_dir, state_dir) is RecoveryState.DISCARD


def test_project_lock_is_non_blocking(tmp_path):
    with project_lock(tmp_path):
        with pytest.raises(ProjectLockError):
            with project_lock(tmp_path):
                pass
