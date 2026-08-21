"""Durable, reader-safe delivery for chapter production runs.

The queue persists delivery metadata only.  ``ChapterProductionRunner`` remains the
single owner of drafting, Book lifecycle changes, review creation, and draft recovery.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from living_narrative.book.coordinator import plan_generation
from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.book.production_admission import (
    ProductionAdmissionController,
    ProductionAdmissionLease,
    ProductionAdmissionRequest,
    load_project_production_admission,
)
from living_narrative.book.production_runner import (
    ChapterProductionRunner,
    ChapterProductionRunStatus,
)
from living_narrative.state.diff import fsync_directory
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import ProjectLockError, project_lock
from living_narrative.workspace.loader import WorkspacePaths, load_project


class QueueJobState(StrEnum):
    """Delivery state for one idempotent chapter production request."""

    QUEUED = "queued"
    LEASED = "leased"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ProductionQueueCorruptionError(ValueError):
    """The durable queue artifact is malformed or violates its schema."""


class ProductionQueueJobNotFoundError(ValueError):
    """No durable delivery job exists for the requested chapter."""


class ProductionQueueLeaseError(ValueError):
    """A worker attempted to complete a job without its current lease."""


class _QueueJob(BaseModel):
    job_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    chapter_id: str = Field(min_length=1)
    state: QueueJobState
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)
    delivery_count: int = Field(default=0, ge=0)
    lease_generation: int = Field(default=0, ge=0)
    worker_id: str | None = None
    lease_heartbeat_at: str | None = None
    lease_expires_at: str | None = None
    run_id: str | None = None
    failure_code: str | None = None
    status: ChapterProductionRunStatus | None = None


class _QueueSnapshot(BaseModel):
    schema_version: int = 1
    jobs: list[_QueueJob] = Field(default_factory=list)


class ProductionQueueStatus(BaseModel):
    """Reader-safe status projection for a durable delivery job."""

    job_id: str
    chapter_id: str
    state: QueueJobState
    delivery_count: int
    run_id: str | None = None
    failure_code: str | None = None
    status: ChapterProductionRunStatus | None = None


class ProductionQueueMetrics(BaseModel):
    """Read-only, aggregate operational metrics with no private execution payload."""

    total_jobs: int = Field(ge=0)
    queued_jobs: int = Field(ge=0)
    leased_jobs: int = Field(ge=0)
    completed_jobs: int = Field(ge=0)
    failed_jobs: int = Field(ge=0)
    stopped_jobs: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    oldest_lease_age_seconds: int | None = Field(default=None, ge=0)
    failure_code_counts: dict[str, int] = Field(default_factory=dict)


@dataclass(frozen=True)
class _QueueClaim:
    job_id: str
    worker_id: str
    lease_generation: int
    lock_fd: int


@dataclass(frozen=True)
class WorkerRunResult:
    """Result of one bounded worker poll, with no private execution payload."""

    claimed: bool
    status: ChapterProductionRunStatus | None = None
    job_id: str | None = None


_DEFAULT_LEASE_SECONDS = 60


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ProductionQueueCorruptionError("queue timestamp must include a timezone")
    return parsed.astimezone(UTC)


def _atomic_write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            yaml.safe_dump(payload, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _read_snapshot(path: Path) -> _QueueSnapshot:
    if not path.is_file():
        return _QueueSnapshot()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return _QueueSnapshot.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ProductionQueueCorruptionError("chapter production queue is invalid") from exc


def _write_event(events_dir: Path, event: str, details: dict[str, Any]) -> None:
    existing = sorted(events_dir.glob("*.yaml")) if events_dir.exists() else []
    _atomic_write_yaml(
        events_dir / f"{len(existing) + 1:06d}_{event}.yaml",
        {
            "schema_version": 1,
            "event": event,
            "recorded_at": _timestamp(_utc_now()),
            **details,
        },
    )


def collect_production_queue_metrics(project_yaml: Path) -> ProductionQueueMetrics:
    """Aggregate durable queue health without exposing job identity, content, or paths."""
    read = load_project(project_yaml)
    if not read.is_valid or read.paths is None:
        raise ValueError(f"invalid project: {project_yaml}")
    paths = read.paths
    with project_lock(paths.root):
        jobs = _read_snapshot(paths.runs / "chapter_production_queue" / "queue.yaml").jobs
    counts = {state: 0 for state in QueueJobState}
    lease_ages: list[int] = []
    failure_code_counts: dict[str, int] = {}
    now = _utc_now()
    for job in jobs:
        counts[job.state] += 1
        if job.failure_code is not None:
            failure_code_counts[job.failure_code] = failure_code_counts.get(job.failure_code, 0) + 1
        if job.state is QueueJobState.LEASED and job.lease_heartbeat_at is not None:
            age_seconds = int((now - _parse_timestamp(job.lease_heartbeat_at)).total_seconds())
            lease_ages.append(max(0, age_seconds))
    return ProductionQueueMetrics(
        total_jobs=len(jobs),
        queued_jobs=counts[QueueJobState.QUEUED],
        leased_jobs=counts[QueueJobState.LEASED],
        completed_jobs=counts[QueueJobState.COMPLETED],
        failed_jobs=counts[QueueJobState.FAILED],
        stopped_jobs=counts[QueueJobState.STOPPED],
        retry_count=sum(max(0, job.delivery_count - 1) for job in jobs),
        oldest_lease_age_seconds=max(lease_ages, default=None),
        failure_code_counts=failure_code_counts,
    )


class DurableProductionQueue:
    """Persist idempotent chapter-production delivery without storing private content."""

    def __init__(self, *, lease_seconds: int = _DEFAULT_LEASE_SECONDS) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self._lease_seconds = lease_seconds

    def enqueue(self, project_yaml: Path, chapter_id: str) -> ProductionQueueStatus:
        """Create or return the current idempotent delivery job for one chapter."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            key = self._idempotency_key(paths, chapter_id)
            existing = next((job for job in snapshot.jobs if job.idempotency_key == key), None)
            if existing is not None:
                if existing.state in {QueueJobState.FAILED, QueueJobState.STOPPED}:
                    now = _timestamp(_utc_now())
                    existing.state = QueueJobState.QUEUED
                    existing.failure_code = None
                    existing.status = None
                    existing.updated_at = now
                    _write_event(
                        self._events_dir(paths),
                        "requeued",
                        {
                            "job_id": existing.job_id,
                            "chapter_id": chapter_id,
                            "idempotency_key": key,
                        },
                    )
                    self._write_snapshot(paths, snapshot)
                return self._status(existing)

            now = _timestamp(_utc_now())
            job_id = f"queue_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:20]}"
            job = _QueueJob(
                job_id=job_id,
                idempotency_key=key,
                chapter_id=chapter_id,
                state=QueueJobState.QUEUED,
                created_at=now,
                updated_at=now,
            )
            _write_event(
                self._events_dir(paths),
                "enqueued",
                {"job_id": job_id, "chapter_id": chapter_id, "idempotency_key": key},
            )
            snapshot.jobs.append(job)
            self._write_snapshot(paths, snapshot)
            return self._status(job)

    def status(self, project_yaml: Path, chapter_id: str) -> ProductionQueueStatus:
        """Return the latest durable delivery projection for one chapter."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            matches = [job for job in snapshot.jobs if job.chapter_id == chapter_id]
            if not matches:
                raise ProductionQueueJobNotFoundError(chapter_id)
            return self._status(max(matches, key=lambda job: job.updated_at))

    def stop(self, project_yaml: Path, chapter_id: str) -> ProductionQueueStatus:
        """Stop a queued delivery before a worker invokes the production runner."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            matches = [job for job in snapshot.jobs if job.chapter_id == chapter_id]
            if not matches:
                raise ProductionQueueJobNotFoundError(chapter_id)
            job = max(matches, key=lambda item: item.updated_at)
            if job.state is QueueJobState.QUEUED:
                lifecycle = StateStore.load(paths.state).book_ledger.chapter(chapter_id).lifecycle
                job.state = QueueJobState.STOPPED
                job.status = ChapterProductionRunStatus(
                    run_id=f"chapter_{chapter_id}_pending",
                    chapter_id=chapter_id,
                    phase="stopped",
                    lifecycle=lifecycle,
                    stopped_reason="author_requested",
                )
                job.updated_at = _timestamp(_utc_now())
                _write_event(
                    self._events_dir(paths),
                    "stopped",
                    {"job_id": job.job_id, "chapter_id": chapter_id},
                )
                self._write_snapshot(paths, snapshot)
            return self._status(job)

    def claim(self, project_yaml: Path, worker_id: str) -> _QueueClaim | None:
        """Claim one queued or expired job while retaining its OS lock for the caller."""
        if not worker_id:
            raise ValueError("worker_id must not be empty")
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            now = _utc_now()
            leased = [job for job in snapshot.jobs if job.state is QueueJobState.LEASED]
            candidates = (
                [job for job in leased if self._claimable(job, now)]
                if leased
                else [job for job in snapshot.jobs if job.state is QueueJobState.QUEUED]
            )
            for job in candidates:
                fd = self._try_lock_job(paths, job.job_id)
                if fd is None:
                    continue
                try:
                    lease_generation = job.lease_generation + 1
                    job.state = QueueJobState.LEASED
                    job.worker_id = worker_id
                    job.lease_generation = lease_generation
                    job.delivery_count += 1
                    job.lease_heartbeat_at = _timestamp(now)
                    job.lease_expires_at = _timestamp(now + timedelta(seconds=self._lease_seconds))
                    job.updated_at = _timestamp(now)
                    _write_event(
                        self._events_dir(paths),
                        "leased",
                        {
                            "job_id": job.job_id,
                            "chapter_id": job.chapter_id,
                            "worker_id": worker_id,
                            "lease_generation": lease_generation,
                        },
                    )
                    self._write_snapshot(paths, snapshot)
                    return _QueueClaim(job.job_id, worker_id, lease_generation, fd)
                except Exception:
                    self._unlock_job(fd)
                    raise
        return None

    def job_for_claim(self, project_yaml: Path, claim: _QueueClaim) -> str:
        """Resolve the chapter ID after validating that the caller still owns the lease."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            job = self._job_for_claim(paths, claim)
            return job.chapter_id

    def heartbeat(self, project_yaml: Path, claim: _QueueClaim) -> ProductionQueueStatus:
        """Renew an owned lease without exposing worker metadata to callers."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            job = self._find_job(snapshot, claim.job_id)
            self._assert_claim(job, claim)
            now = _utc_now()
            job.lease_heartbeat_at = _timestamp(now)
            job.lease_expires_at = _timestamp(now + timedelta(seconds=self._lease_seconds))
            job.updated_at = _timestamp(now)
            _write_event(
                self._events_dir(paths),
                "heartbeat",
                {
                    "job_id": job.job_id,
                    "chapter_id": job.chapter_id,
                    "lease_generation": job.lease_generation,
                },
            )
            self._write_snapshot(paths, snapshot)
            return self._status(job)

    def defer(self, project_yaml: Path, claim: _QueueClaim, reason: str) -> None:
        """Return an owned delivery to the queue after a temporary admission deferral."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            job = self._find_job(snapshot, claim.job_id)
            self._assert_claim(job, claim)
            job.state = QueueJobState.QUEUED
            job.worker_id = None
            job.lease_heartbeat_at = None
            job.lease_expires_at = None
            job.updated_at = _timestamp(_utc_now())
            _write_event(
                self._events_dir(paths),
                "deferred",
                {"job_id": job.job_id, "chapter_id": job.chapter_id, "reason": reason},
            )
            self._write_snapshot(paths, snapshot)

    def complete(
        self,
        project_yaml: Path,
        claim: _QueueClaim,
        status: ChapterProductionRunStatus,
    ) -> None:
        """Record completed delivery after a runner returns a reader-safe status."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            job = self._find_job(snapshot, claim.job_id)
            self._assert_claim(job, claim)
            job.state = QueueJobState.COMPLETED
            job.run_id = status.run_id
            job.status = status
            job.worker_id = None
            job.lease_heartbeat_at = None
            job.lease_expires_at = None
            job.updated_at = _timestamp(_utc_now())
            _write_event(
                self._events_dir(paths),
                "completed",
                {
                    "job_id": job.job_id,
                    "chapter_id": job.chapter_id,
                    "run_id": status.run_id,
                    "phase": status.phase.value,
                },
            )
            self._write_snapshot(paths, snapshot)

    def fail(self, project_yaml: Path, claim: _QueueClaim, exc: Exception) -> None:
        """Record a sanitized terminal delivery failure for an owned lease."""
        paths = self._paths(project_yaml)
        with project_lock(paths.root):
            snapshot = _read_snapshot(self._snapshot_path(paths))
            job = self._find_job(snapshot, claim.job_id)
            self._assert_claim(job, claim)
            code = type(exc).__name__.lower()
            job.state = QueueJobState.FAILED
            job.failure_code = code
            job.worker_id = None
            job.lease_heartbeat_at = None
            job.lease_expires_at = None
            job.updated_at = _timestamp(_utc_now())
            _write_event(
                self._events_dir(paths),
                "failed",
                {"job_id": job.job_id, "chapter_id": job.chapter_id, "failure_code": code},
            )
            self._write_snapshot(paths, snapshot)

    def release(self, claim: _QueueClaim) -> None:
        """Release a job lock after the worker has published its delivery result."""
        self._unlock_job(claim.lock_fd)

    def _paths(self, project_yaml: Path) -> WorkspacePaths:
        read = load_project(project_yaml)
        if not read.is_valid or read.paths is None:
            raise ValueError(f"invalid project: {project_yaml}")
        return read.paths

    def _idempotency_key(self, paths: WorkspacePaths, chapter_id: str) -> str:
        bundle = StateStore.load(paths.state)
        generation = plan_generation(bundle)
        attempts = load_chapter_lineage(paths.root / "books" / "chapters", chapter_id).attempts
        return f"{generation}:{chapter_id}:{len(attempts) + 1}"

    @staticmethod
    def _queue_dir(paths: WorkspacePaths) -> Path:
        return paths.runs / "chapter_production_queue"

    def _snapshot_path(self, paths: WorkspacePaths) -> Path:
        return self._queue_dir(paths) / "queue.yaml"

    def _events_dir(self, paths: WorkspacePaths) -> Path:
        return self._queue_dir(paths) / "events"

    def _locks_dir(self, paths: WorkspacePaths) -> Path:
        return self._queue_dir(paths) / "locks"

    def _write_snapshot(self, paths: WorkspacePaths, snapshot: _QueueSnapshot) -> None:
        _atomic_write_yaml(
            self._snapshot_path(paths),
            snapshot.model_dump(mode="json", exclude_none=True),
        )

    def _try_lock_job(self, paths: WorkspacePaths, job_id: str) -> int | None:
        locks_dir = self._locks_dir(paths)
        locks_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(locks_dir / f"{job_id}.lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                return None
            raise
        return fd

    @staticmethod
    def _unlock_job(fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _claimable(self, job: _QueueJob, now: datetime) -> bool:
        if job.state is QueueJobState.QUEUED:
            return True
        if job.state is not QueueJobState.LEASED or job.lease_expires_at is None:
            return False
        return _parse_timestamp(job.lease_expires_at) <= now

    @staticmethod
    def _find_job(snapshot: _QueueSnapshot, job_id: str) -> _QueueJob:
        job = next((item for item in snapshot.jobs if item.job_id == job_id), None)
        if job is None:
            raise ProductionQueueJobNotFoundError(job_id)
        return job

    def _job_for_claim(self, paths: WorkspacePaths, claim: _QueueClaim) -> _QueueJob:
        snapshot = _read_snapshot(self._snapshot_path(paths))
        job = self._find_job(snapshot, claim.job_id)
        self._assert_claim(job, claim)
        return job

    @staticmethod
    def _assert_claim(job: _QueueJob, claim: _QueueClaim) -> None:
        if (
            job.state is not QueueJobState.LEASED
            or job.worker_id != claim.worker_id
            or job.lease_generation != claim.lease_generation
        ):
            raise ProductionQueueLeaseError(claim.job_id)

    @staticmethod
    def _status(job: _QueueJob) -> ProductionQueueStatus:
        return ProductionQueueStatus(
            job_id=job.job_id,
            chapter_id=job.chapter_id,
            state=job.state,
            delivery_count=job.delivery_count,
            run_id=job.run_id,
            failure_code=job.failure_code,
            status=job.status,
        )


class DurableProductionWorker:
    """Run at most one leased chapter delivery through the existing production runner."""

    def __init__(
        self,
        queue: DurableProductionQueue | None = None,
        *,
        heartbeat_interval_seconds: float = 20.0,
        admission_controller: ProductionAdmissionController | None = None,
        admission_request: Callable[[Path], ProductionAdmissionRequest] | None = None,
    ) -> None:
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        if (admission_controller is None) != (admission_request is None):
            raise ValueError(
                "admission_controller and admission_request must be configured together"
            )
        self._queue = queue or DurableProductionQueue()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._admission_controller = admission_controller
        self._admission_request = admission_request

    def run_once(self, project_yaml: Path, *, worker_id: str) -> WorkerRunResult:
        """Claim one job, execute the runner once, and durably publish the outcome."""
        claim = self._queue.claim(project_yaml, worker_id)
        if claim is None:
            return WorkerRunResult(claimed=False)
        stop_heartbeats = threading.Event()
        heartbeat_thread: threading.Thread | None = None
        admission_lease: ProductionAdmissionLease | None = None
        admission_controller = self._admission_controller
        admission_request = self._admission_request
        try:
            chapter_id = self._queue.job_for_claim(project_yaml, claim)
            if admission_controller is None:
                configured = load_project_production_admission(project_yaml)
                if configured is not None:
                    admission_controller = configured.controller
                    admission_request = configured.request_for
            if admission_controller is not None and admission_request is not None:
                request = admission_request(project_yaml)
                decision = admission_controller.try_admit(request)
                if not decision.allowed:
                    self._queue.defer(
                        project_yaml,
                        claim,
                        decision.reason or "admission temporarily unavailable",
                    )
                    return WorkerRunResult(claimed=False)
                assert decision.lease is not None
                admission_lease = decision.lease
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_until_done,
                args=(project_yaml, claim, stop_heartbeats),
                daemon=True,
            )
            heartbeat_thread.start()
            status = ChapterProductionRunner().run(project_yaml, chapter_id)
            stop_heartbeats.set()
            heartbeat_thread.join(timeout=self._heartbeat_interval_seconds + 1.0)
            heartbeat_thread = None
            self._queue.complete(project_yaml, claim, status)
            return WorkerRunResult(claimed=True, status=status, job_id=claim.job_id)
        except Exception as exc:
            stop_heartbeats.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=self._heartbeat_interval_seconds + 1.0)
                heartbeat_thread = None
            self._queue.fail(project_yaml, claim, exc)
            raise
        finally:
            stop_heartbeats.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=self._heartbeat_interval_seconds + 1.0)
            if admission_lease is not None:
                assert admission_controller is not None
                admission_controller.release(admission_lease)
            self._queue.release(claim)

    def _heartbeat_until_done(
        self,
        project_yaml: Path,
        claim: _QueueClaim,
        stop_heartbeats: threading.Event,
    ) -> None:
        while not stop_heartbeats.wait(self._heartbeat_interval_seconds):
            try:
                self._queue.heartbeat(project_yaml, claim)
            except ProductionQueueLeaseError:
                return
            except ProjectLockError:
                continue


__all__ = [
    "DurableProductionQueue",
    "DurableProductionWorker",
    "ProductionQueueCorruptionError",
    "ProductionQueueJobNotFoundError",
    "ProductionQueueLeaseError",
    "ProductionQueueMetrics",
    "ProductionQueueStatus",
    "collect_production_queue_metrics",
    "QueueJobState",
    "WorkerRunResult",
]
