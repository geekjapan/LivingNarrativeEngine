"""Project-scoped locking and the state commit journal protocol."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import re
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from living_narrative.state.diff import (
    StateDiff,
    StateDiffApplyResult,
    apply_state_diff,
    fsync_directory,
    save_apply_artifacts,
)
from living_narrative.state.models import WorldStateBundle
from living_narrative.state.store import StateStore, _bundle_files


class ProjectLockError(BlockingIOError):
    """Raised when another process already owns a project's mutation lock."""


RecoveryTarget = Literal["project", "rollback_journal", "doctor"]


class RecoveryError(RuntimeError):
    """Raised when an unsafe incomplete turn blocks a state mutation."""

    def __init__(
        self,
        message: str,
        *,
        target: RecoveryTarget = "project",
        quarantine: bool = False,
    ) -> None:
        if quarantine:
            if target == "project":
                message = (
                    f"{message}; restore a backup or manually repair the state, "
                    "then run `living-narrative doctor`"
                )
            elif target == "rollback_journal":
                message = f"{message}; manually repair the rollback journal before retrying"
            else:
                message = (
                    f"{message}; quarantine cannot be cleared safely; restore a backup "
                    "or manually repair the state"
                )
        super().__init__(message)


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


class TransactionFaultPoint(StrEnum):
    """Crash-injection boundaries for the commit journal protocol."""

    INTENT_BEFORE = "intent_before"
    INTENT_AFTER_SAVE_BEFORE = "intent_after_save_before"
    SAVE_MID = "save_mid"
    SAVE_AFTER_META_BEFORE = "save_after_meta_before"
    META_MID = "meta_mid"


TransactionFaultHook = Callable[[TransactionFaultPoint, int], None]


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
    on_commit: Callable[[], None] | None = None,
    fault_hook: TransactionFaultHook | None = None,
) -> StateDiffApplyResult:
    """Apply and persist one diff using the journal-before-state ordering.

    ``on_commit`` runs after the diff's own artifacts are saved but *before* the commit
    intent is journalled and the state is published, so callers can fold their turn
    artifacts (``state_diff.yaml``, ``review.yaml``, ...) into the recoverable transaction.
    The commit intent — and therefore the applied ``meta.yaml`` marker that recovery may
    reconstruct from it — is written only once every caller artifact is durable, so an
    applied turn can never be missing them, even for a no-op diff whose before/after state
    hashes are equal (where the live hash already matches ``state_hash_after``).

    ``fault_hook`` receives a named boundary and the number of completed writes in
    that boundary. A hook may raise to leave a deterministic crash fixture behind.
    """
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
    if on_commit is not None:
        on_commit()
    _call_fault_hook(fault_hook, TransactionFaultPoint.INTENT_BEFORE, 0)
    _atomic_write_yaml(turn_dir / "commit_intent.yaml", intent.model_dump(mode="json"))
    _call_fault_hook(fault_hook, TransactionFaultPoint.INTENT_AFTER_SAVE_BEFORE, 1)
    state_write_number = 0

    def after_state_write(_path: Path) -> None:
        nonlocal state_write_number
        state_write_number += 1
        _call_fault_hook(fault_hook, TransactionFaultPoint.SAVE_MID, state_write_number)

    StateStore.save(result.bundle, resolved_state_dir, on_write=after_state_write)
    _call_fault_hook(fault_hook, TransactionFaultPoint.SAVE_AFTER_META_BEFORE, state_write_number)
    _write_commit_meta(turn_dir, meta, intent, fault_hook=fault_hook)
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


def classify_recovery_state(
    turn_dir: Path | None,
    state_dir: Path,
    *,
    apply: bool = True,
) -> RecoveryState:
    """Classify and, for safe cases, recover an incomplete turn.

    Mutation callers invoke this immediately after taking the project lock.  ``apply=False``
    is for read-only diagnostics such as ``doctor``.
    """
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
        state = RecoveryState.BLOCKED if meta is None else RecoveryState.DISCARD
    else:
        current_hash = state_hash(state_dir)
        if (
            meta is not None
            and meta.get("status") == "applied"
            and current_hash == intent.state_hash_after
        ):
            return RecoveryState.CLEAN
        if current_hash == intent.state_hash_after:
            state = RecoveryState.RECOVER_META
        elif current_hash == intent.state_hash_before:
            state = RecoveryState.DISCARD
        else:
            state = RecoveryState.QUARANTINE

    if apply:
        apply_recovery_state(turn_dir, state)
    return state


def apply_recovery_state(turn_dir: Path, state: RecoveryState) -> bool:
    if state is RecoveryState.RECOVER_META:
        intent = read_commit_intent(turn_dir)
        if intent is not None:
            _write_commit_meta(turn_dir, None, intent)
            return True
        return False
    if state is not RecoveryState.DISCARD:
        return False

    # A legacy applied turn has no journal to recover.  Keep it as live history; the
    # existing turn-number resolver will advance past it as before Issue 066.
    if read_commit_intent(turn_dir) is None:
        meta = _read_mapping(turn_dir / "meta.yaml")
        if meta is not None and meta.get("status") == "applied":
            return False
    from living_narrative.pipeline.turn_numbering import discard_turn_directory

    discard_turn_directory(turn_dir)
    return True


def finalize_rollback_renames(
    runs_dir: Path,
    journal_dir: Path,
    *,
    from_turn: int,
    to_turn: int,
) -> list[Path]:
    """Archive the rolled-back canonical turn dirs and mark the journal terminal.

    Idempotent: only turns still present as ``turn_NNNN`` are renamed aside, and the
    journal is stamped ``renames_complete`` so recovery does not revisit it.
    """
    from living_narrative.pipeline.turn_numbering import rollback_turn_directory, turn_dir_path

    renamed: list[Path] = []
    for turn in range(to_turn + 1, from_turn + 1):
        canonical = turn_dir_path(runs_dir, turn)
        if canonical.exists():
            renamed.append(rollback_turn_directory(canonical))
    meta = dict(_read_mapping(journal_dir / "meta.yaml") or {})
    meta["renames_complete"] = True
    _atomic_write_yaml(journal_dir / "meta.yaml", meta)
    return renamed


def recover_rollback_journals(runs_dir: Path, state_dir: Path) -> None:
    """Complete the turn-dir archival of any rollback whose state commit finished but
    whose renames did not (e.g. a crash between the two phases).

    Mutation entry points call this right after taking the project lock, before they
    trust ``latest_turn_directory``: otherwise the pre-rollback highest turn is still
    canonical and classifies against a hash that matches neither its before nor after
    state, spuriously quarantining a project whose rollback journal actually completed.
    """
    tx_dir = runs_dir / ".transactions"
    if not tx_dir.exists():
        return
    for journal_dir in sorted(tx_dir.glob("rollback_*")):
        if not journal_dir.is_dir():
            continue
        meta = _read_mapping(journal_dir / "meta.yaml")
        if meta is None or meta.get("status") != "applied" or meta.get("renames_complete"):
            continue
        intent = read_commit_intent(journal_dir)
        if intent is None or state_hash(state_dir) != intent.state_hash_after:
            continue
        from_turn = meta.get("rollback_from_turn")
        to_turn = meta.get("turn")
        if from_turn is None or to_turn is None:
            continue
        finalize_rollback_renames(
            runs_dir, journal_dir, from_turn=int(from_turn), to_turn=int(to_turn)
        )


def rotate_completed_rollback_journal(journal_dir: Path) -> Path | None:
    """Archive a fully-completed rollback journal aside so its name can be reused.

    A rollback names its journal ``rollback_<from>_to_<to>`` deterministically, so rolling
    back the same range again reuses the directory. A prior *terminal* journal (already
    applied and ``renames_complete``) carries stale hashes that no longer match the live
    state, which would make ``classify_recovery_state`` report ``QUARANTINE`` and block the
    new, valid rollback. Move it to ``..._done_<n>`` (D112 spirit: never destroy history);
    an incomplete/unrecovered journal is left in place so its real recovery state surfaces.
    """
    meta = _read_mapping(journal_dir / "meta.yaml")
    if meta is None or not meta.get("renames_complete"):
        return None
    n = 1
    while True:
        candidate = journal_dir.with_name(f"{journal_dir.name}_done_{n}")
        if not candidate.exists():
            break
        n += 1
    journal_dir.rename(candidate)
    return candidate


def _write_commit_meta(
    turn_dir: Path,
    meta: Mapping[str, Any] | None,
    intent: CommitIntent,
    *,
    fault_hook: TransactionFaultHook | None = None,
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
    _atomic_write_yaml(
        turn_dir / "meta.yaml",
        data,
        after_temp_write=lambda: _call_fault_hook(fault_hook, TransactionFaultPoint.META_MID, 1),
    )


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


def _atomic_write_yaml(
    path: Path,
    data: Any,
    *,
    after_temp_write: Callable[[], None] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            stream.write(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
            stream.flush()
            os.fsync(stream.fileno())
        if after_temp_write is not None:
            after_temp_write()
        os.replace(tmp, path)
        fsync_directory(path.parent)
    finally:
        tmp.unlink(missing_ok=True)


def _call_fault_hook(
    hook: TransactionFaultHook | None,
    point: TransactionFaultPoint,
    write_number: int,
) -> None:
    if hook is not None:
        hook(point, write_number)


__all__ = [
    "CommitIntent",
    "ProjectLockError",
    "RecoveryError",
    "RecoveryClassification",
    "RecoveryTarget",
    "RecoveryState",
    "TransactionFaultHook",
    "TransactionFaultPoint",
    "apply_recovery_state",
    "classify_recovery_state",
    "commit_state_diff",
    "finalize_rollback_renames",
    "latest_turn_directory",
    "recover_rollback_journals",
    "project_lock",
    "read_commit_intent",
    "rotate_completed_rollback_journal",
    "state_hash",
]
