"""Project-scoped locking and the state commit journal protocol."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from living_narrative.state.diff import (
    StateDiff,
    StateDiffApplyResult,
    apply_state_diff,
    save_apply_artifacts,
)
from living_narrative.state.models import WorldStateBundle
from living_narrative.state.store import StateStore, _bundle_files


class ProjectLockError(BlockingIOError):
    """Raised when another process already owns a project's mutation lock."""


class RecoveryError(RuntimeError):
    """Raised when an unsafe incomplete turn blocks a state mutation."""


@contextmanager
def project_lock(project_root: Path) -> Iterator[Path]:
    """Hold the non-blocking POSIX lock at ``project_root/.lock``."""
    project_root.mkdir(parents=True, exist_ok=True)
    lock_path = project_root / ".lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise ProjectLockError(f"project is already locked: {project_root}") from exc
            raise
        yield lock_path
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


class RecoveryState(StrEnum):
    CLEAN = "clean"
    RECOVER_META = "recover_meta"
    META_COMPLETE = "recover_meta"
    DISCARD = "discard"
    QUARANTINE = "quarantine"
    BLOCKED = "blocked"


RecoveryClassification = RecoveryState


class CommitIntent(BaseModel):
    state_hash_before: str = Field(min_length=1)
    state_hash_after: str = Field(min_length=1)
    diff_id: str = Field(min_length=1)
    rng_start_offset: int = Field(ge=0)


def state_hash(state_dir: Path) -> str:
    """Hash every YAML file in a state directory using canonical YAML."""
    return _hash_entries(_read_state_entries(_resolve_state_dir(state_dir)))


def _state_hash_for_bundle(state_dir: Path, bundle: WorldStateBundle) -> str:
    entries = _read_state_entries(state_dir)
    entries.update(_bundle_files(bundle))
    return _hash_entries(entries)


def commit_state_diff(
    bundle: WorldStateBundle,
    diff: StateDiff,
    state_dir: Path,
    turn_dir: Path,
    *,
    rng_start_offset: int = 0,
    selected_change_indexes: set[int] | None = None,
    meta: Mapping[str, Any] | None = None,
) -> StateDiffApplyResult:
    """Apply and persist one diff using the journal-before-state ordering."""
    result = apply_state_diff(bundle, diff, selected_change_indexes)
    resolved_state_dir = _resolve_state_dir(state_dir)
    state_hash_before = state_hash(resolved_state_dir)
    state_hash_after = _state_hash_for_bundle(resolved_state_dir, result.bundle)
    intent = CommitIntent(
        state_hash_before=state_hash_before,
        state_hash_after=state_hash_after,
        diff_id=diff.id,
        rng_start_offset=rng_start_offset,
    )

    save_apply_artifacts(result, turn_dir)
    _atomic_write_yaml(turn_dir / "commit_intent.yaml", intent.model_dump(mode="json"))
    StateStore.save(result.bundle, resolved_state_dir)
    _write_commit_meta(turn_dir, meta, intent)
    return result


def read_commit_intent(turn_dir: Path) -> CommitIntent | None:
    path = turn_dir / "commit_intent.yaml"
    if not path.exists():
        return None
    try:
        return CommitIntent.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except (OSError, yaml.YAMLError, ValueError):
        return None


def latest_turn_directory(runs_dir: Path) -> Path | None:
    """Return the latest canonical turn directory, if one exists."""
    candidates: list[tuple[int, Path]] = []
    if not runs_dir.exists():
        return None
    for entry in runs_dir.iterdir():
        if not entry.is_dir():
            continue
        match = re.fullmatch(r"turn_(\d+)", entry.name)
        if match is not None:
            candidates.append((int(match.group(1)), entry))
    return max(candidates, default=(0, None))[1]


def classify_recovery_state(turn_dir: Path | None, state_dir: Path) -> RecoveryState:
    """Classify an incomplete turn by comparing its intent hashes to live state."""
    if turn_dir is None or not turn_dir.exists():
        return RecoveryState.CLEAN
    meta = _read_mapping(turn_dir / "meta.yaml")
    intent = read_commit_intent(turn_dir)
    if intent is None:
        if (turn_dir / "commit_intent.yaml").exists():
            return RecoveryState.QUARANTINE
        if meta is not None and meta.get("status") in {
            "pending_review",
            "stopped_for_review",
            "failed",
        }:
            return RecoveryState.CLEAN
        return RecoveryState.BLOCKED if meta is None else RecoveryState.DISCARD

    current_hash = state_hash(state_dir)
    if (
        meta is not None
        and meta.get("status") == "applied"
        and current_hash == intent.state_hash_after
    ):
        return RecoveryState.CLEAN
    if current_hash == intent.state_hash_after:
        return RecoveryState.RECOVER_META
    if current_hash == intent.state_hash_before:
        return RecoveryState.DISCARD
    return RecoveryState.QUARANTINE


def _write_commit_meta(
    turn_dir: Path,
    meta: Mapping[str, Any] | None,
    intent: CommitIntent,
) -> None:
    data = dict(_read_mapping(turn_dir / "meta.yaml") or {})
    data.update(meta or {})
    data.update(
        {
            "status": "applied",
            "state_hash_before": intent.state_hash_before,
            "state_hash_after": intent.state_hash_after,
            "diff_id": intent.diff_id,
            "rng_start_offset": intent.rng_start_offset,
        }
    )
    _atomic_write_yaml(turn_dir / "meta.yaml", data)


def _resolve_state_dir(path: Path) -> Path:
    return path if path.name == "state" or (path / "world.yaml").exists() else path / "state"


def _read_state_entries(state_dir: Path) -> dict[Path, Any]:
    entries: dict[Path, Any] = {}
    if not state_dir.exists():
        return entries
    for path in sorted(state_dir.rglob("*.yaml")):
        if not path.is_file():
            continue
        relative = path.relative_to(state_dir)
        raw = path.read_text(encoding="utf-8")
        try:
            entries[relative] = yaml.safe_load(raw)
        except yaml.YAMLError:
            entries[relative] = {"__invalid_yaml__": raw}
    return entries


def _hash_entries(entries: Mapping[Path, Any]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(entries):
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(
            yaml.safe_dump(entries[relative], allow_unicode=True, sort_keys=True).encode("utf-8")
        )
        digest.update(b"\0")
    return digest.hexdigest()


def _read_mapping(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            stream.write(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        _fsync_directory(path.parent)
    finally:
        tmp.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


__all__ = [
    "CommitIntent",
    "ProjectLockError",
    "RecoveryError",
    "RecoveryClassification",
    "RecoveryState",
    "classify_recovery_state",
    "commit_state_diff",
    "latest_turn_directory",
    "project_lock",
    "read_commit_intent",
    "state_hash",
]
