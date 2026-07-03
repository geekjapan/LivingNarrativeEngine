"""GM review gate resolution for pending turn diffs."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from living_narrative.intervention.history import append_history, build_history_entries
from living_narrative.pipeline.status import TurnStatus
from living_narrative.pipeline.turn_numbering import discard_turn_directory
from living_narrative.state.diff import StateDiff, apply_state_diff, save_apply_artifacts
from living_narrative.state.models import Event, UserMode
from living_narrative.state.store import StateStore


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
    status: TurnStatus


@dataclass(frozen=True)
class ReviewResult:
    decision: ReviewDecision
    resulting_turn_status: TurnStatus | None
    turn_dir: Path
    discarded_turn_dir: Path | None = None


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


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
    resulting_turn_status: TurnStatus | None = None,
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
        data["resulting_turn_status"] = resulting_turn_status.value
    _atomic_write_yaml(turn_dir / "review.yaml", data)


def update_meta_status(turn_dir: Path, status: TurnStatus) -> None:
    path = turn_dir / "meta.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    data["status"] = status.value
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
    decision = ReviewDecision(decision)
    original_diff = read_artifact_diff(turn_dir)
    if decision == ReviewDecision.RERUN_TURN:
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

    if decision != ReviewDecision.REJECT_ALL:
        bundle = StateStore.load(state_dir)
        apply_result = apply_state_diff(bundle, applied_diff)
        StateStore.save(apply_result.bundle, state_dir)
        save_apply_artifacts(apply_result, turn_dir)

    write_artifact_diff(turn_dir, applied_diff, applied=True)
    write_review_yaml(
        turn_dir,
        turn=original_diff.turn,
        decision=decision,
        decided_by=decided_by,
        applied_change_indices=sorted(selected) if selected is not None else None,
        edit_diff=applied_diff if decision == ReviewDecision.EDIT else None,
        resulting_turn_status=TurnStatus.APPLIED,
    )
    update_meta_status(turn_dir, TurnStatus.APPLIED)
    _append_deferred_history(workspace_root, turn_dir, applied_diff)
    return ReviewResult(decision, TurnStatus.APPLIED, turn_dir)
