"""GM review gate resolution for pending turn diffs."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from living_narrative.intervention.history import append_history, build_history_entries
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event, UserMode
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import (
    RecoveryError,
    RecoveryState,
    classify_recovery_state,
    commit_state_diff,
    latest_turn_directory,
    project_lock,
)

UNRESOLVED_STATUS_VALUES = {"pending_review", "stopped_for_review"}
APPLIED_STATUS = "applied"


class ReviewDecision(StrEnum):
    ACCEPT_ALL = "accept_all"
    REJECT_ALL = "reject_all"
    PARTIAL = "partial"
    EDIT = "edit"
    RERUN_TURN = "rerun_turn"


@dataclass(frozen=True)
class PendingReview:
    turn: int
    turn_dir: Path
    diff: StateDiff
    status: Any


@dataclass(frozen=True)
class ReviewResult:
    decision: ReviewDecision
    resulting_turn_status: Any | None
    turn_dir: Path
    discarded_turn_dir: Path | None = None


class ReviewStateError(ValueError):
    pass


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            stream.write(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def read_artifact_diff(turn_dir: Path) -> StateDiff:
    data = yaml.safe_load((turn_dir / "state_diff.yaml").read_text(encoding="utf-8")) or {}
    return StateDiff.model_validate(data["diff"] if "diff" in data else data)


def write_artifact_diff(turn_dir: Path, diff: StateDiff, *, applied: bool) -> None:
    data = {}
    path = turn_dir / "state_diff.yaml"
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data["diff"] = diff.model_dump(mode="json")
    data["applied"] = applied
    data.setdefault("rejected_changes", [])
    _atomic_write_yaml(path, data)


def write_review_yaml(
    turn_dir: Path,
    *,
    turn: int,
    decision: ReviewDecision,
    decided_by: UserMode | str,
    applied_change_indices: list[int] | None = None,
    edit_diff: StateDiff | None = None,
    resulting_turn_status: Any | None = None,
    auto_applied: bool = False,
) -> None:
    decision = ReviewDecision(decision)
    data: dict[str, Any] = {
        "turn": turn,
        "decision": decision.value,
        "decided_at": datetime.now(UTC).isoformat(),
        "decided_by": UserMode(decided_by).value,
        "auto_applied": auto_applied,
    }
    if applied_change_indices is not None:
        data["applied_change_indices"] = applied_change_indices
    if edit_diff is not None:
        data["edit_diff"] = edit_diff.model_dump(mode="json")
    if resulting_turn_status is not None:
        data["resulting_turn_status"] = getattr(
            resulting_turn_status, "value", resulting_turn_status
        )
    _atomic_write_yaml(turn_dir / "review.yaml", data)


def update_meta_status(turn_dir: Path, status: Any) -> None:
    path = turn_dir / "meta.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    data["status"] = getattr(status, "value", status)
    _atomic_write_yaml(path, data)


def _load_events(turn_dir: Path) -> list[Event]:
    path = turn_dir / "events.yaml"
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Event.model_validate(item) for item in raw]


def _load_interventions(turn_dir: Path) -> list[dict[str, Any]]:
    path = turn_dir / "intervention.yaml"
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw.get("interventions", [])


def _append_deferred_history(workspace_root: Path, turn_dir: Path, diff: StateDiff) -> None:
    interventions = _load_interventions(turn_dir)
    if not interventions:
        return
    entries = build_history_entries(interventions, _load_events(turn_dir), diff)
    append_history(workspace_root / "interventions.yaml", entries)


def resolve_review(
    *,
    workspace_root: Path,
    state_dir: Path,
    turn_dir: Path,
    decision: ReviewDecision | str,
    decided_by: UserMode | str,
    selected_change_indices: set[int] | None = None,
    edited_diff: StateDiff | dict[str, Any] | None = None,
) -> ReviewResult:
    with project_lock(workspace_root):
        return _resolve_review_locked(
            workspace_root=workspace_root,
            state_dir=state_dir,
            turn_dir=turn_dir,
            decision=decision,
            decided_by=decided_by,
            selected_change_indices=selected_change_indices,
            edited_diff=edited_diff,
        )


def _resolve_review_locked(
    *,
    workspace_root: Path,
    state_dir: Path,
    turn_dir: Path,
    decision: ReviewDecision | str,
    decided_by: UserMode | str,
    selected_change_indices: set[int] | None = None,
    edited_diff: StateDiff | dict[str, Any] | None = None,
) -> ReviewResult:
    recovery_state = classify_recovery_state(
        latest_turn_directory(turn_dir.parent),
        state_dir,
    )
    if recovery_state in {RecoveryState.QUARANTINE, RecoveryState.BLOCKED}:
        raise RecoveryError(
            f"cannot mutate project while recovery state is {recovery_state.value}",
            quarantine=recovery_state is RecoveryState.QUARANTINE,
        )
    from living_narrative.pipeline.turn_numbering import read_turn_status

    decision = ReviewDecision(decision)
    status = read_turn_status(turn_dir)
    status_value = getattr(status, "value", None)
    if status_value not in UNRESOLVED_STATUS_VALUES:
        found = status.value if status is not None else "missing"
        raise ReviewStateError(f"turn {turn_dir.name} is not pending review; status={found}")
    original_diff = read_artifact_diff(turn_dir)
    if decision == ReviewDecision.RERUN_TURN:
        from living_narrative.pipeline.turn_numbering import discard_turn_directory

        write_review_yaml(
            turn_dir,
            turn=original_diff.turn,
            decision=decision,
            decided_by=decided_by,
        )
        return ReviewResult(decision, None, turn_dir, discard_turn_directory(turn_dir))

    if decision == ReviewDecision.REJECT_ALL:
        applied_diff = original_diff.model_copy(update={"changes": []}, deep=True)
        selected = set()
    elif decision == ReviewDecision.PARTIAL:
        selected = selected_change_indices or set()
        changes = [
            change for index, change in enumerate(original_diff.changes) if index in selected
        ]
        applied_diff = original_diff.model_copy(update={"changes": changes}, deep=True)
        _atomic_write_yaml(
            turn_dir / "state_diff_pre_review.yaml", original_diff.model_dump(mode="json")
        )
    elif decision == ReviewDecision.EDIT:
        applied_diff = (
            StateDiff.model_validate(edited_diff) if isinstance(edited_diff, dict) else edited_diff
        )
        if applied_diff is None:
            raise ValueError("edited_diff is required for edit review decision")
        selected = None
        _atomic_write_yaml(
            turn_dir / "state_diff_pre_review.yaml", original_diff.model_dump(mode="json")
        )
    else:
        applied_diff = original_diff
        selected = None

    def _finalize_review_artifacts() -> None:
        # For a committed review these run inside the transaction (before the state is
        # published) so a resolved turn can never end up applied without its artifact
        # diff and review record.
        write_artifact_diff(turn_dir, applied_diff, applied=True)
        write_review_yaml(
            turn_dir,
            turn=original_diff.turn,
            decision=decision,
            decided_by=decided_by,
            applied_change_indices=sorted(selected) if selected is not None else None,
            edit_diff=applied_diff if decision == ReviewDecision.EDIT else None,
            resulting_turn_status=APPLIED_STATUS,
        )

    if decision != ReviewDecision.REJECT_ALL:
        bundle = StateStore.load(state_dir)
        meta = yaml.safe_load((turn_dir / "meta.yaml").read_text(encoding="utf-8")) or {}
        commit_state_diff(
            bundle,
            applied_diff,
            state_dir,
            turn_dir,
            rng_start_offset=int(meta.get("rng_start_offset") or 0),
            meta={"turn": original_diff.turn, "commit_mode": "review"},
            on_commit=_finalize_review_artifacts,
        )
    else:
        # No state mutation to journal; write the artifacts directly, still before the
        # applied marker below.
        _finalize_review_artifacts()

    update_meta_status(turn_dir, APPLIED_STATUS)
    _append_deferred_history(workspace_root, turn_dir, applied_diff)
    return ReviewResult(decision, APPLIED_STATUS, turn_dir)
