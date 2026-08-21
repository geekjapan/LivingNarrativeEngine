"""Admission policy for cross-book chapter-production delivery."""

from __future__ import annotations

import fcntl
import hashlib
import os
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from living_narrative.state.diff import fsync_directory
from living_narrative.workspace.loader import load_project


class ProductionAdmissionPolicy(BaseModel):
    """Configured limits applied before a worker starts a chapter delivery."""

    max_active_deliveries: int | None = Field(default=None, ge=1)
    admission_lease_seconds: int | None = Field(default=None, ge=1)
    provider_window_seconds: int | None = Field(default=None, ge=1)
    max_deliveries_per_provider_window: int | None = Field(default=None, ge=1)


class ProjectProductionAdmissionConfig(ProductionAdmissionPolicy):
    """Opt-in project configuration for a shared scheduler namespace."""

    scheduler_root: str = Field(min_length=1)
    forecast_usd: Decimal | None = Field(default=None, ge=0)


class ProductionAdmissionRequest(BaseModel):
    """Reader-safe request to start one delivery in a scheduler namespace."""

    book_id: str = Field(min_length=1)
    provider_profile_id: str = Field(min_length=1)
    actual_usd: Decimal | None = Field(default=None, ge=0)
    forecast_usd: Decimal | None = Field(default=None, ge=0)
    hard_usd: Decimal | None = Field(default=None, ge=0)


@dataclass(frozen=True)
class ProductionAdmissionLease:
    """Opaque ownership token returned only to the admitting worker."""

    admission_id: str


@dataclass(frozen=True)
class ProjectProductionAdmission:
    """Resolved opt-in controller and reader-safe request identity for one project."""

    controller: ProductionAdmissionController
    book_id: str
    provider_profile_id: str
    forecast_usd: Decimal | None

    def request_for(self, project_yaml: Path) -> ProductionAdmissionRequest:
        """Build a stable reader-safe request for the configured project."""
        del project_yaml
        return ProductionAdmissionRequest(
            book_id=self.book_id,
            provider_profile_id=self.provider_profile_id,
            forecast_usd=self.forecast_usd,
        )


class ProductionAdmissionDecision(BaseModel):
    """Reader-safe result of one admission attempt."""

    allowed: bool
    reason: str | None = None
    lease: ProductionAdmissionLease | None = None


class ProductionAdmissionMetrics(BaseModel):
    """Reader-safe operational projection for one scheduler namespace."""

    active_admissions: int = 0
    reserved_usd: Decimal = Decimal(0)
    deferred_reason_counts: dict[str, int] = Field(default_factory=dict)
    oldest_admission_age_seconds: int | None = None


class _ActiveAdmission(BaseModel):
    admission_id: str = Field(min_length=1)
    book_id: str = Field(min_length=1)
    provider_profile_id: str = Field(min_length=1)
    admitted_at: str = Field(min_length=1)
    forecast_usd: Decimal | None = Field(default=None, ge=0)


class _ProviderAdmission(BaseModel):
    provider_profile_id: str = Field(min_length=1)
    admitted_at: str = Field(min_length=1)


class _AdmissionSnapshot(BaseModel):
    schema_version: int = 1
    active_admissions: list[_ActiveAdmission] = Field(default_factory=list)
    provider_admissions: list[_ProviderAdmission] = Field(default_factory=list)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("admission timestamp must include a timezone")
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


def _read_snapshot(path: Path) -> _AdmissionSnapshot:
    if not path.is_file():
        return _AdmissionSnapshot()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return _AdmissionSnapshot.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
        raise ValueError("production admission snapshot is invalid") from exc


def load_project_production_admission(
    project_yaml: Path,
) -> ProjectProductionAdmission | None:
    """Load explicit admission configuration; absent configuration preserves v0.6 behavior."""
    path = project_yaml.parent / "production_admission.yaml"
    if not path.is_file():
        return None
    read = load_project(project_yaml)
    if not read.is_valid or read.config is None:
        raise ValueError(f"invalid project: {project_yaml}")
    try:
        config = ProjectProductionAdmissionConfig.model_validate(
            yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        )
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
        raise ValueError("production admission config is invalid") from exc
    root = Path(config.scheduler_root)
    scheduler_root = root if root.is_absolute() else project_yaml.parent / root
    profile_name = read.config.llm_bindings.get("chapter_draft")
    provider_profile_id = (
        f"profile:{profile_name}"
        if profile_name is not None
        else f"default:{read.config.llm.provider}:{read.config.llm.model}"
    )
    book_id = hashlib.sha256(read.config.id.encode("utf-8")).hexdigest()[:16]
    return ProjectProductionAdmission(
        controller=ProductionAdmissionController(scheduler_root, policy=config),
        book_id=book_id,
        provider_profile_id=provider_profile_id,
        forecast_usd=config.forecast_usd,
    )


def collect_production_admission_metrics(
    scheduler_root: Path,
    *,
    now: datetime | None = None,
) -> ProductionAdmissionMetrics:
    """Read durable admission state without exposing production-private data."""
    snapshot = _read_snapshot(scheduler_root / "admission.yaml")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    ages = [
        max(0, int((current - _parse_timestamp(admission.admitted_at)).total_seconds()))
        for admission in snapshot.active_admissions
    ]
    deferred_reasons: Counter[str] = Counter()
    events_dir = scheduler_root / "events"
    for path in sorted(events_dir.glob("*.yaml")) if events_dir.is_dir() else []:
        try:
            event = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if event.get("event") == "deferred" and isinstance(event.get("reason"), str):
            deferred_reasons[event["reason"]] += 1
    return ProductionAdmissionMetrics(
        active_admissions=len(snapshot.active_admissions),
        reserved_usd=sum(
            (admission.forecast_usd or Decimal(0)) for admission in snapshot.active_admissions
        ),
        deferred_reason_counts=dict(sorted(deferred_reasons.items())),
        oldest_admission_age_seconds=max(ages) if ages else None,
    )


class ProductionAdmissionController:
    """Limit concurrently admitted chapter deliveries within one scheduler namespace."""

    def __init__(
        self,
        scheduler_root: Path,
        *,
        policy: ProductionAdmissionPolicy,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._scheduler_root = scheduler_root
        self._policy = policy
        self._clock = clock or (lambda: datetime.now(UTC))
        self._leases: dict[str, _ActiveAdmission] = {}
        self._provider_admissions: list[_ProviderAdmission] = []
        self._sequence = 0
        self._reload_snapshot()

    @property
    def _snapshot_path(self) -> Path:
        return self._scheduler_root / "admission.yaml"

    def try_admit(self, request: ProductionAdmissionRequest) -> ProductionAdmissionDecision:
        """Admit one delivery unless a configured limit has been reached."""
        with self._locked():
            self._reload_snapshot()
            return self._try_admit_locked(request)

    def _try_admit_locked(self, request: ProductionAdmissionRequest) -> ProductionAdmissionDecision:
        now = self._clock()
        self._expire_leases(now)
        provider_admissions = self._active_provider_admissions(now)
        if (
            self._policy.provider_window_seconds is not None
            and self._policy.max_deliveries_per_provider_window is not None
        ):
            provider_deliveries = sum(
                admission.provider_profile_id == request.provider_profile_id
                for admission in provider_admissions
            )
            if provider_deliveries >= self._policy.max_deliveries_per_provider_window:
                return self._defer("provider rate limit reached")
        if request.hard_usd is not None:
            if request.actual_usd is None or request.forecast_usd is None:
                return self._defer("book hard USD budget cannot be evaluated")
            active_reserved_usd = sum(
                admission.forecast_usd or Decimal(0)
                for admission in self._leases.values()
                if admission.book_id == request.book_id
            )
            if request.actual_usd + active_reserved_usd + request.forecast_usd > request.hard_usd:
                return self._defer("book hard USD budget exceeded")
        if (
            self._policy.max_active_deliveries is not None
            and len(self._leases) >= self._policy.max_active_deliveries
        ):
            return self._defer("parallel delivery limit reached")
        self._sequence += 1
        lease = ProductionAdmissionLease(admission_id=f"admission_{self._sequence:06d}")
        self._leases[lease.admission_id] = _ActiveAdmission(
            admission_id=lease.admission_id,
            book_id=request.book_id,
            provider_profile_id=request.provider_profile_id,
            admitted_at=_timestamp(now),
            forecast_usd=request.forecast_usd,
        )
        self._provider_admissions = [
            *provider_admissions,
            _ProviderAdmission(
                provider_profile_id=request.provider_profile_id,
                admitted_at=_timestamp(now),
            ),
        ]
        self._write_event(
            "admitted",
            {
                "admission_id": lease.admission_id,
                "book_id": request.book_id,
                "provider_profile_id": request.provider_profile_id,
                "forecast_usd": str(request.forecast_usd) if request.forecast_usd else None,
            },
        )
        self._write_snapshot()
        return ProductionAdmissionDecision(allowed=True, lease=lease)

    def release(self, lease: ProductionAdmissionLease) -> None:
        """Release an active delivery admission after the worker exits."""
        with self._locked():
            self._reload_snapshot()
            admission = self._leases.pop(lease.admission_id, None)
            if admission is not None:
                self._write_event(
                    "released",
                    {
                        "admission_id": admission.admission_id,
                        "book_id": admission.book_id,
                        "provider_profile_id": admission.provider_profile_id,
                    },
                )
            self._write_snapshot()

    def _expire_leases(self, now: datetime) -> None:
        if self._policy.admission_lease_seconds is None:
            return
        cutoff = now - timedelta(seconds=self._policy.admission_lease_seconds)
        self._leases = {
            admission_id: admission
            for admission_id, admission in self._leases.items()
            if _parse_timestamp(admission.admitted_at) > cutoff
        }

    def _active_provider_admissions(self, now: datetime) -> list[_ProviderAdmission]:
        if self._policy.provider_window_seconds is None:
            return self._provider_admissions
        cutoff = now - timedelta(seconds=self._policy.provider_window_seconds)
        return [
            admission
            for admission in self._provider_admissions
            if _parse_timestamp(admission.admitted_at) > cutoff
        ]

    def _defer(self, reason: str) -> ProductionAdmissionDecision:
        self._write_event("deferred", {"reason": reason})
        return ProductionAdmissionDecision(allowed=False, reason=reason)

    def _write_event(self, event: str, details: dict[str, Any]) -> None:
        events_dir = self._scheduler_root / "events"
        existing = sorted(events_dir.glob("*.yaml")) if events_dir.exists() else []
        _atomic_write_yaml(
            events_dir / f"{len(existing) + 1:06d}_{event}.yaml",
            {
                "schema_version": 1,
                "event": event,
                "recorded_at": _timestamp(self._clock()),
                **details,
            },
        )

    def _reload_snapshot(self) -> None:
        snapshot = _read_snapshot(self._snapshot_path)
        self._leases = {
            admission.admission_id: admission for admission in snapshot.active_admissions
        }
        self._provider_admissions = snapshot.provider_admissions
        self._sequence = max(
            (int(admission_id.rsplit("_", 1)[-1]) for admission_id in self._leases),
            default=0,
        )

    @contextmanager
    def _locked(self):
        self._scheduler_root.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._scheduler_root / "admission.lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _write_snapshot(self) -> None:
        snapshot = _AdmissionSnapshot(
            active_admissions=list(self._leases.values()),
            provider_admissions=self._provider_admissions,
        )
        _atomic_write_yaml(
            self._snapshot_path,
            snapshot.model_dump(mode="json", exclude_none=True),
        )
