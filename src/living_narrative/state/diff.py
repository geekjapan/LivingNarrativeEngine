"""StateDiff validation, apply, inverse generation, and rollback helpers."""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from living_narrative.state.ids import id_type, validate_relationship_key
from living_narrative.state.models import (
    CanonEntry,
    GmVaultEntry,
    ReaderStateEntry,
    TimelineEntry,
    UnresolvedThread,
    Visibility,
    WorldStateBundle,
)

DiffId = id_type("diff")
EventId = id_type("event")
Target = Literal[
    "world",
    "character",
    "scene",
    "reader_state",
    "canon",
    "gm_vault",
    "relationship",
    "timeline",
    "threads",
]
Op = Literal["add", "remove", "set", "delta"]
COLLECTION_TARGETS = {"canon", "reader_state", "gm_vault", "timeline", "threads"}
# 014: "threads" is the diff-target name for the bundle's `unresolved_threads` collection
# (kept short/stable in diff artifacts; the attribute name is the longer bundle field).
_TARGET_ATTR = {"threads": "unresolved_threads"}


class StateDiffError(ValueError):
    pass


class AppliedChange(BaseModel):
    change_id: int
    clamped: bool = False
    original_value: Any = None
    computed_value: Any = None
    final_value: Any = None


class StateDiffChange(BaseModel):
    target: Target
    op: Op
    path: str = ""
    value: Any = None
    id: str | None = None
    visibility: Visibility
    source_event: EventId | None = None

    @field_validator("id")
    @classmethod
    def _validate_relationship_id(cls, value: str | None, info) -> str | None:
        if value is not None and info.data.get("target") == "relationship":
            validate_relationship_key(value)
        return value

    @model_validator(mode="after")
    def _validate_target_id(self) -> StateDiffChange:
        if self.target == "relationship":
            if self.id is None:
                raise ValueError("relationship change requires id")
            validate_relationship_key(self.id)
        elif self.target in {"character", "scene"} and self.id is None:
            raise ValueError(f"{self.target} change requires id")
        return self


class StateDiff(BaseModel):
    id: DiffId
    turn: int
    changes: list[StateDiffChange] = Field(default_factory=list)


class InverseStateDiff(StateDiff):
    pass


class StateDiffApplyResult(BaseModel):
    bundle: WorldStateBundle
    inverse_diff: InverseStateDiff
    applied_changes: list[AppliedChange] = Field(default_factory=list)


def apply_state_diff(
    bundle: WorldStateBundle,
    diff: StateDiff,
    selected_change_indexes: set[int] | None = None,
) -> StateDiffApplyResult:
    working = bundle.model_copy(deep=True)
    applied: list[AppliedChange] = []
    inverse_changes: list[StateDiffChange] = []
    changes = [
        change
        for index, change in enumerate(diff.changes)
        if selected_change_indexes is None or index in selected_change_indexes
    ]

    try:
        for index, change in enumerate(changes):
            inverse, report = _apply_change(working, change, index)
            inverse_changes.insert(0, inverse)
            applied.append(report)
    except Exception as exc:
        raise StateDiffError(str(exc)) from exc

    return StateDiffApplyResult(
        bundle=working,
        inverse_diff=InverseStateDiff(id=diff.id, turn=diff.turn, changes=inverse_changes),
        applied_changes=applied,
    )


def save_apply_artifacts(result: StateDiffApplyResult, artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(artifact_dir / "inverse_diff.yaml", result.inverse_diff.model_dump(mode="json"))
    _write_yaml(
        artifact_dir / "apply_report.yaml",
        {"applied_changes": [change.model_dump(mode="json") for change in result.applied_changes]},
    )


def rollback(bundle: WorldStateBundle, inverse_diffs: list[InverseStateDiff]) -> WorldStateBundle:
    current = bundle
    for diff in sorted(inverse_diffs, key=lambda item: item.turn, reverse=True):
        current = apply_state_diff(current, diff).bundle
    return current


def load_inverse_diff(path: Path) -> InverseStateDiff:
    return InverseStateDiff.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def _apply_change(
    bundle: WorldStateBundle,
    change: StateDiffChange,
    index: int,
) -> tuple[StateDiffChange, AppliedChange]:
    if change.target in COLLECTION_TARGETS and change.path == "":
        current = getattr(bundle, _TARGET_ATTR.get(change.target, change.target))
        old_value = deepcopy(current)
        report = AppliedChange(change_id=index, original_value=old_value)
        if change.op == "add":
            current.append(_model_for_target(change.target).model_validate(change.value))
            inverse_op, inverse_value = "remove", change.value
        elif change.op == "remove":
            removed = _remove_value(current, change)
            inverse_op, inverse_value = "add", removed
        else:
            raise StateDiffError(f"{change.op} is not supported at {change.target} root")
        inverse = StateDiffChange(
            target=change.target,
            id=change.id,
            op=inverse_op,
            path=change.path,
            value=inverse_value,
            visibility=change.visibility,
            source_event=change.source_event,
        )
        return inverse, report

    target = _target_object(bundle, change)
    container, key = _resolve_path(target, change.path)
    old_value = _read(container, key)
    report = AppliedChange(change_id=index, original_value=deepcopy(old_value))

    if change.op == "set":
        _write(container, key, change.value)
        inverse_op, inverse_value = "set", old_value
    elif change.op == "delta":
        if not isinstance(old_value, int):
            raise StateDiffError(f"delta requires numeric field: {change.path}")
        raw = old_value + change.value
        new_value = max(0, min(100, raw))
        _write(container, key, new_value)
        report.computed_value = raw
        report.final_value = new_value
        report.clamped = raw != new_value
        inverse_op, inverse_value = (
            ("set", old_value) if report.clamped else ("delta", -change.value)
        )
    elif change.op == "add":
        if not isinstance(old_value, list):
            raise StateDiffError(f"add requires list path: {change.path}")
        old_value.append(change.value)
        inverse_op, inverse_value = "remove", change.value
    elif change.op == "remove":
        removed = _remove_value(old_value, change)
        inverse_op, inverse_value = "add", removed
    else:  # pragma: no cover - pydantic validates op
        raise StateDiffError(f"unsupported op {change.op}")

    inverse = StateDiffChange(
        target=change.target,
        id=change.id,
        op=inverse_op,
        path=change.path,
        value=inverse_value,
        visibility=change.visibility,
        source_event=change.source_event,
    )
    return inverse, report


def _target_object(bundle: WorldStateBundle, change: StateDiffChange) -> Any:
    if change.target == "world":
        return bundle.world
    if change.target == "character":
        return _find_by_id(bundle.characters, change.id)
    if change.target == "scene":
        return _find_by_id(bundle.scenes, change.id)
    if change.target == "relationship":
        from_id, to_id = change.id.split("__")
        for relationship in bundle.relationships:
            if relationship.from_ == from_id and relationship.to == to_id:
                return relationship
        raise StateDiffError(f"relationship not found: {change.id}")

    collection = getattr(bundle, _TARGET_ATTR.get(change.target, change.target))
    return _find_by_id(collection, change.id)


def _resolve_path(target: Any, path: str) -> tuple[Any, str | int]:
    if path == "":
        return target, ""
    current = target
    parts = path.split(".")
    for part in parts[:-1]:
        current = _read(current, part)
    return current, parts[-1]


def _read(container: Any, key: str | int) -> Any:
    if key == "":
        return container
    if isinstance(container, list):
        for item in container:
            if getattr(item, "id", None) == key:
                return item
        raise StateDiffError(f"path not found: {key}")
    if isinstance(container, dict):
        if key not in container:
            raise StateDiffError(f"path not found: {key}")
        return container[key]
    if isinstance(container, BaseModel):
        attr = "from_" if key == "from" else key
        if not hasattr(container, attr):
            raise StateDiffError(f"path not found: {key}")
        return getattr(container, attr)
    raise StateDiffError(f"path not traversable: {key}")


def _write(container: Any, key: str | int, value: Any) -> None:
    if isinstance(container, dict):
        container[key] = value
        return
    if isinstance(container, BaseModel):
        attr = "from_" if key == "from" else key
        current = getattr(container, attr, None)
        # enum欄へのset(YAML由来のraw str)は型を維持して書き戻す
        if isinstance(current, Enum) and not isinstance(value, Enum):
            value = type(current)(value)
        setattr(container, attr, value)
        return
    raise StateDiffError(f"path not writable: {key}")


def _remove_value(current: Any, change: StateDiffChange) -> Any:
    if not isinstance(current, list):
        raise StateDiffError(f"remove requires list path: {change.path}")
    value = change.value
    if value is None and change.id is not None:
        for item in current:
            if getattr(item, "id", None) == change.id:
                current.remove(item)
                return item.model_dump(mode="json") if isinstance(item, BaseModel) else item
    if isinstance(value, dict) and "id" in value:
        for item in current:
            if getattr(item, "id", None) == value["id"]:
                current.remove(item)
                return item.model_dump(mode="json") if isinstance(item, BaseModel) else item
    if isinstance(value, dict):
        for item in current:
            if isinstance(item, BaseModel) and item.model_dump(mode="json") == value:
                current.remove(item)
                return item.model_dump(mode="json")
    if value in current:
        current.remove(value)
        return value
    raise StateDiffError("remove target not found")


def _find_by_id(items: list[Any], id_: str | None) -> Any:
    for item in items:
        if getattr(item, "id", None) == id_:
            return item
    raise StateDiffError(f"target not found: {id_}")


def _model_for_target(target: str) -> type[BaseModel]:
    return {
        "canon": CanonEntry,
        "reader_state": ReaderStateEntry,
        "gm_vault": GmVaultEntry,
        "timeline": TimelineEntry,
        "threads": UnresolvedThread,
    }[target]


def _write_yaml(path: Path, data: Any) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
