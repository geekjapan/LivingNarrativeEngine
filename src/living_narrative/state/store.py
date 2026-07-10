"""Load and save workspace state files."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from living_narrative.state.models import (
    CanonEntry,
    CharacterState,
    FactionState,
    GmVaultEntry,
    MemorySummary,
    ReaderStateEntry,
    RelationshipState,
    SceneState,
    TimelineEntry,
    UnresolvedThread,
    VisualProfilesState,
    WorldState,
    WorldStateBundle,
)
from living_narrative.workspace.layout import REQUIRED_STATE_FILES

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StateValidationIssue:
    file_path: Path
    field_path: str
    message: str


class StateLoadError(Exception):
    def __init__(self, issues: list[StateValidationIssue]) -> None:
        self.issues = issues
        super().__init__("state load failed")


class StateStore:
    @staticmethod
    def load(workspace_path: Path) -> WorldStateBundle:
        state_dir = _state_dir(workspace_path)
        issues: list[StateValidationIssue] = []

        for filename in REQUIRED_STATE_FILES:
            path = state_dir / filename
            if not path.exists():
                issues.append(
                    StateValidationIssue(path, "<file>", "required state file is missing")
                )
        if issues:
            raise StateLoadError(issues)

        world = _load_one(state_dir / "world.yaml", WorldState, issues)
        factions = _load_list(state_dir / "factions.yaml", FactionState, issues, optional=True)
        characters = _load_dir(state_dir / "characters", CharacterState, issues)
        scenes = _load_dir(state_dir / "scenes", SceneState, issues)
        relationships = _load_list(state_dir / "relationships.yaml", RelationshipState, issues)
        canon = _load_list(state_dir / "canon.yaml", CanonEntry, issues)
        reader_state = _load_list(state_dir / "reader_state.yaml", ReaderStateEntry, issues)
        gm_vault = _load_list(state_dir / "gm_vault.yaml", GmVaultEntry, issues)
        timeline = _load_list(state_dir / "timeline.yaml", TimelineEntry, issues)
        unresolved_threads = _load_list(
            state_dir / "unresolved_threads.yaml",
            UnresolvedThread,
            issues,
        )
        # Issue 015: optional like factions.yaml (back-compat, loads empty when absent) since
        # existing projects predate the memory-summary feature and interval defaults to 0/off.
        memory_summaries = _load_list(
            state_dir / "memory_summaries.yaml",
            MemorySummary,
            issues,
            optional=True,
        )
        visual_profiles = _load_optional_one(
            state_dir / "visual_profiles.yaml",
            VisualProfilesState,
            issues,
        )

        if issues:
            raise StateLoadError(issues)

        bundle = WorldStateBundle(
            world=world,
            factions=factions,
            characters=characters,
            relationships=relationships,
            scenes=scenes,
            canon=canon,
            reader_state=reader_state,
            gm_vault=gm_vault,
            timeline=timeline,
            unresolved_threads=unresolved_threads,
            memory_summaries=memory_summaries,
            visual_profiles=visual_profiles,
        )
        _warn_unknowns(bundle, state_dir)
        return bundle

    @staticmethod
    def save(bundle: WorldStateBundle, workspace_path: Path) -> None:
        state_dir = _state_dir(workspace_path)
        state_dir.mkdir(parents=True, exist_ok=True)
        _atomic_yaml(state_dir / "world.yaml", _dump_model(bundle.world))
        _atomic_yaml(state_dir / "factions.yaml", [_dump_model(item) for item in bundle.factions])
        _atomic_yaml(
            state_dir / "relationships.yaml",
            [_dump_model(item) for item in bundle.relationships],
        )
        _atomic_yaml(state_dir / "canon.yaml", [_dump_model(item) for item in bundle.canon])
        _atomic_yaml(
            state_dir / "reader_state.yaml",
            [_dump_model(item) for item in bundle.reader_state],
        )
        _atomic_yaml(state_dir / "gm_vault.yaml", [_dump_model(item) for item in bundle.gm_vault])
        _atomic_yaml(state_dir / "timeline.yaml", [_dump_model(item) for item in bundle.timeline])
        _atomic_yaml(
            state_dir / "unresolved_threads.yaml",
            [_dump_model(item) for item in bundle.unresolved_threads],
        )
        _atomic_yaml(
            state_dir / "memory_summaries.yaml",
            [_dump_model(item) for item in bundle.memory_summaries],
        )
        _atomic_yaml(state_dir / "visual_profiles.yaml", _dump_model(bundle.visual_profiles))
        _save_dir(state_dir / "characters", bundle.characters)
        _save_dir(state_dir / "scenes", bundle.scenes)


def _state_dir(workspace_path: Path) -> Path:
    if workspace_path.name == "state" or (workspace_path / "world.yaml").exists():
        return workspace_path
    return workspace_path / "state"


def _load_yaml(path: Path, optional: bool = False) -> Any:
    if optional and not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_one(path: Path, model: type[BaseModel], issues: list[StateValidationIssue]) -> Any:
    try:
        return model.model_validate(_load_yaml(path) or {})
    except ValidationError as exc:
        _collect_validation_errors(path, exc, issues)
        return None


def _load_optional_one(
    path: Path,
    model: type[BaseModel],
    issues: list[StateValidationIssue],
) -> Any:
    if not path.exists():
        return model()
    return _load_one(path, model, issues)


def _load_list(
    path: Path,
    model: type[BaseModel],
    issues: list[StateValidationIssue],
    optional: bool = False,
) -> list[Any]:
    raw = _load_yaml(path, optional=optional) or []
    if not isinstance(raw, list):
        issues.append(StateValidationIssue(path, "<root>", "expected a list"))
        return []
    values = []
    for index, item in enumerate(raw):
        try:
            values.append(model.model_validate(item or {}))
        except ValidationError as exc:
            _collect_validation_errors(path, exc, issues, prefix=str(index))
    return values


def _load_dir(path: Path, model: type[BaseModel], issues: list[StateValidationIssue]) -> list[Any]:
    if not path.exists():
        return []
    values = []
    for file_path in sorted(path.glob("*.yaml")):
        value = _load_one(file_path, model, issues)
        if value is not None:
            values.append(value)
    return values


def _collect_validation_errors(
    path: Path,
    exc: ValidationError,
    issues: list[StateValidationIssue],
    prefix: str | None = None,
) -> None:
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"]) or "<root>"
        if prefix is not None:
            field = f"{prefix}.{field}"
        issues.append(StateValidationIssue(path, field, error["msg"]))


def _warn_unknowns(value: Any, state_dir: Path, path: Path | None = None) -> None:
    current_path = path or state_dir
    if isinstance(value, BaseModel):
        for key in sorted(value.model_extra or {}):
            LOGGER.warning("Unknown field %s in %s", key, current_path)
        for name in value.__class__.model_fields:
            child = getattr(value, name)
            _warn_unknowns(child, state_dir, current_path)
    elif isinstance(value, list):
        for child in value:
            _warn_unknowns(child, state_dir, current_path)


def _save_dir(path: Path, values: list[BaseModel]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for value in values:
        _atomic_yaml(path / f"{value.id}.yaml", _dump_model(value))


def _dump_model(model: BaseModel) -> dict[str, Any]:
    data: dict[str, Any] = {}
    dumped = model.model_dump(mode="json", by_alias=True)
    for key in model.__class__.model_fields:
        alias = model.__class__.model_fields[key].alias or key
        if alias in dumped:
            data[alias] = _dump_value(dumped[alias])
    for key in sorted(model.model_extra or {}):
        data[key] = _dump_value(model.model_extra[key])
    return data


def _dump_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _dump_model(value)
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump_value(item) for key, item in value.items()}
    return value


def _atomic_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)
