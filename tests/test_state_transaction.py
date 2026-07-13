import pytest
import yaml

from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Visibility
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import (
    ProjectLockError,
    RecoveryError,
    RecoveryState,
    TransactionFaultPoint,
    classify_recovery_state,
    commit_state_diff,
    finalize_rollback_renames,
    project_lock,
    recover_rollback_journals,
    rotate_completed_rollback_journal,
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


def test_recovery_error_guidance_is_scoped_to_the_recovery_target():
    project = RecoveryError(
        "cannot mutate project while recovery state is quarantine",
        target="project",
        quarantine=True,
    )
    journal = RecoveryError(
        "cannot mutate project while rollback journal recovery state is quarantine",
        target="rollback_journal",
        quarantine=True,
    )
    doctor = RecoveryError(
        "cannot repair project while recovery state is quarantine",
        target="doctor",
        quarantine=True,
    )

    assert "restore a backup" in str(project)
    assert "doctor" in str(project)
    assert "restore a backup" not in str(journal)
    assert "doctor" not in str(journal)
    assert "doctor" not in str(doctor)


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


def test_on_commit_artifacts_are_durable_before_state_is_published(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    before = StateStore.load(state_dir)
    before_hash = state_hash(state_dir)
    observed: dict[str, object] = {}

    def _write_artifacts() -> None:
        # The live state must still be the pre-commit state, and the applied marker
        # must not yet exist, when the caller writes its turn artifacts.
        observed["state_hash"] = state_hash(state_dir)
        observed["meta_exists"] = (turn_dir / "meta.yaml").exists()
        (turn_dir / "state_diff.yaml").write_text("artifact\n", encoding="utf-8")

    commit_state_diff(before, _diff(), state_dir, turn_dir, on_commit=_write_artifacts)

    assert observed["state_hash"] == before_hash
    assert observed["meta_exists"] is False
    # Reaching hash_after (a CLEAN/RECOVER_META classification) therefore guarantees the
    # artifact is already on disk.
    assert (turn_dir / "state_diff.yaml").read_text(encoding="utf-8") == "artifact\n"
    assert state_hash(state_dir) != before_hash
    assert classify_recovery_state(turn_dir, state_dir) is RecoveryState.CLEAN


def _noop_diff() -> StateDiff:
    return StateDiff(id="diff_0001", turn=1, changes=[])


def test_on_commit_runs_before_the_commit_intent_is_journalled(tmp_path, build_project):
    # A no-op diff has before == after, so the live hash already equals state_hash_after and
    # RECOVER_META would fire the instant commit_intent.yaml exists. The artifacts must be
    # durable *before* the intent, so recovery can never stamp an applied turn without them.
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    # Normalize the on-disk state to its serialized form so an empty diff is a true no-op
    # (its re-serialized bundle is byte-identical, hence before == after).
    StateStore.save(StateStore.load(state_dir), state_dir)
    observed: dict[str, object] = {}

    def _on_commit() -> None:
        observed["intent_exists"] = (turn_dir / "commit_intent.yaml").exists()
        (turn_dir / "state_diff.yaml").write_text("artifact\n", encoding="utf-8")

    commit_state_diff(
        StateStore.load(state_dir), _noop_diff(), state_dir, turn_dir, on_commit=_on_commit
    )

    assert observed["intent_exists"] is False
    intent = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    assert intent["state_hash_before"] == intent["state_hash_after"]
    assert (turn_dir / "state_diff.yaml").exists()
    assert classify_recovery_state(turn_dir, state_dir) is RecoveryState.CLEAN


def test_commit_state_diff_does_not_publish_when_on_commit_raises(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    before = StateStore.load(state_dir).model_dump(mode="json")

    def _boom() -> None:
        raise RuntimeError("artifact write failed")

    with pytest.raises(RuntimeError, match="artifact write failed"):
        commit_state_diff(StateStore.load(state_dir), _diff(), state_dir, turn_dir, on_commit=_boom)

    # on_commit runs before the intent and the state publish, so a raising callback leaves
    # no journal, no applied marker, and the state untouched.
    assert not (turn_dir / "commit_intent.yaml").exists()
    assert not (turn_dir / "meta.yaml").exists()
    assert StateStore.load(state_dir).model_dump(mode="json") == before


def test_rotate_completed_rollback_journal_frees_the_name_for_reuse(tmp_path, build_project):
    project_path = build_project(tmp_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    state_dir = project_path.parent / "workspace" / "state"

    # A completed rollback leaves a terminal journal (applied + renames_complete).
    terminal = runs_dir / ".transactions" / "rollback_0003_to_0001"
    commit_state_diff(
        StateStore.load(state_dir),
        _diff("rolled-back"),
        state_dir,
        terminal,
        meta={"turn": 1, "commit_mode": "rollback", "rollback_from_turn": 3},
    )
    finalize_rollback_renames(runs_dir, terminal, from_turn=3, to_turn=1)

    archived = rotate_completed_rollback_journal(terminal)

    assert archived is not None
    assert archived.name == "rollback_0003_to_0001_done_1"
    assert not terminal.exists()

    # An incomplete journal (no renames_complete) is left in place for real recovery.
    incomplete = runs_dir / ".transactions" / "rollback_0005_to_0002"
    commit_state_diff(
        StateStore.load(state_dir),
        _diff("partial"),
        state_dir,
        incomplete,
        meta={"turn": 2, "commit_mode": "rollback", "rollback_from_turn": 5},
    )
    assert rotate_completed_rollback_journal(incomplete) is None
    assert incomplete.exists()


def test_recover_rollback_journals_completes_pending_renames(tmp_path, build_project):
    project_path = build_project(tmp_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    state_dir = project_path.parent / "workspace" / "state"
    (runs_dir / "turn_0002").mkdir(parents=True)
    (runs_dir / "turn_0003").mkdir(parents=True)
    journal_dir = runs_dir / ".transactions" / "rollback_0003_to_0001"

    # Simulate a rollback whose state commit finished but whose renames did not.
    commit_state_diff(
        StateStore.load(state_dir),
        _diff("rolled-back"),
        state_dir,
        journal_dir,
        meta={"turn": 1, "commit_mode": "rollback", "rollback_from_turn": 3},
    )
    assert (runs_dir / "turn_0002").exists()
    assert (runs_dir / "turn_0003").exists()

    recover_rollback_journals(runs_dir, state_dir)

    assert not (runs_dir / "turn_0002").exists()
    assert not (runs_dir / "turn_0003").exists()
    assert list(runs_dir.glob("turn_0002_rolledback_*"))
    assert list(runs_dir.glob("turn_0003_rolledback_*"))
    journal_meta = yaml.safe_load((journal_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert journal_meta["renames_complete"] is True

    # Idempotent: a second pass is a no-op and does not re-archive anything.
    recover_rollback_journals(runs_dir, state_dir)
    assert len(list(runs_dir.glob("turn_0002_rolledback_*"))) == 1


def test_recover_rollback_journals_skips_incomplete_state_commit(tmp_path, build_project):
    project_path = build_project(tmp_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    state_dir = project_path.parent / "workspace" / "state"
    (runs_dir / "turn_0002").mkdir(parents=True)
    journal_dir = runs_dir / ".transactions" / "rollback_0002_to_0001"
    commit_state_diff(
        StateStore.load(state_dir),
        _diff("rolled-back"),
        state_dir,
        journal_dir,
        meta={"turn": 1, "commit_mode": "rollback", "rollback_from_turn": 2},
    )
    # The live state does not match the journal's recorded hash_after (the state commit
    # phase did not really land), so renames must NOT be completed.
    intent = yaml.safe_load((journal_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    intent["state_hash_after"] = "not-the-live-state"
    (journal_dir / "commit_intent.yaml").write_text(
        yaml.safe_dump(intent, sort_keys=False), encoding="utf-8"
    )

    recover_rollback_journals(runs_dir, state_dir)

    assert (runs_dir / "turn_0002").exists()


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
    assert not turn_dir.exists()
    assert (turn_dir.parent / "turn_0001_discarded_1").exists()


def test_recovery_completes_meta_when_state_matches_after(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"

    commit_state_diff(StateStore.load(state_dir), _diff(), state_dir, turn_dir)
    (turn_dir / "meta.yaml").unlink()

    assert classify_recovery_state(turn_dir, state_dir) is RecoveryState.RECOVER_META
    meta = yaml.safe_load((turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["status"] == "applied"
    assert classify_recovery_state(turn_dir, state_dir, apply=False) is RecoveryState.CLEAN


def test_recovery_quarantine_is_not_mutated(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"

    commit_state_diff(StateStore.load(state_dir), _diff(), state_dir, turn_dir)
    intent = yaml.safe_load((turn_dir / "commit_intent.yaml").read_text(encoding="utf-8"))
    intent["state_hash_after"] = "not-the-live-state"
    (turn_dir / "commit_intent.yaml").write_text(
        yaml.safe_dump(intent, sort_keys=False), encoding="utf-8"
    )

    assert classify_recovery_state(turn_dir, state_dir, apply=False) is RecoveryState.QUARANTINE
    assert turn_dir.exists()


def test_project_lock_is_non_blocking(tmp_path):
    with project_lock(tmp_path):
        with pytest.raises(ProjectLockError):
            with project_lock(tmp_path):
                pass


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        (TransactionFaultPoint.INTENT_BEFORE, RecoveryState.BLOCKED),
        (TransactionFaultPoint.INTENT_AFTER_SAVE_BEFORE, RecoveryState.DISCARD),
        (TransactionFaultPoint.SAVE_MID, RecoveryState.QUARANTINE),
        (TransactionFaultPoint.SAVE_AFTER_META_BEFORE, RecoveryState.RECOVER_META),
        (TransactionFaultPoint.META_MID, RecoveryState.RECOVER_META),
    ],
)
def test_commit_fault_matrix_classifies_partial_turns(tmp_path, build_project, point, expected):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"

    def crash_hook(actual_point, _write_number):
        if actual_point is point:
            raise RuntimeError(f"injected crash at {actual_point.value}")

    with pytest.raises(RuntimeError, match="injected crash"):
        commit_state_diff(
            StateStore.load(state_dir), _diff(), state_dir, turn_dir, fault_hook=crash_hook
        )

    assert classify_recovery_state(turn_dir, state_dir, apply=False) is expected
