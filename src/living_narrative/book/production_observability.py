"""Reader-safe operational projection for durable chapter production."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from living_narrative.book.production_admission import (
    ProductionAdmissionMetrics,
    collect_production_admission_metrics,
    load_project_production_admission,
)
from living_narrative.book.production_queue import (
    ProductionQueueMetrics,
    collect_production_queue_metrics,
)
from living_narrative.workspace.loader import load_project


class ProductionBudgetStopMetrics(BaseModel):
    """Reader-safe aggregate for budget-originated production stops."""

    total_stops: int = Field(default=0, ge=0)
    reason_counts: dict[str, int] = Field(default_factory=dict)


class ProductionOperationalMetrics(BaseModel):
    """Read-only operations view that intentionally contains no book content."""

    queue: ProductionQueueMetrics
    budget_stops: ProductionBudgetStopMetrics = Field(default_factory=ProductionBudgetStopMetrics)
    admission: ProductionAdmissionMetrics | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


_BUDGET_STOP_TAXONOMY = {
    "chapter attempt budget exceeded": "chapter_attempt_limit",
    "book attempt budget exceeded": "book_attempt_limit",
    "consecutive revision budget exceeded": "consecutive_revision_limit",
    "chapter hard USD budget exceeded": "chapter_hard_usd_limit",
    "book hard USD budget exceeded": "book_hard_usd_limit",
}


def collect_production_operational_metrics(project_yaml: Path) -> ProductionOperationalMetrics:
    """Collect the public durable-delivery health projection without state mutation."""
    configured = load_project_production_admission(project_yaml)
    return ProductionOperationalMetrics(
        queue=collect_production_queue_metrics(project_yaml),
        budget_stops=collect_production_budget_stop_metrics(project_yaml),
        admission=(
            collect_production_admission_metrics(configured.scheduler_root)
            if configured is not None
            else None
        ),
    )


def collect_production_budget_stop_metrics(project_yaml: Path) -> ProductionBudgetStopMetrics:
    """Count durable budget stops using only source and normalized public reason codes."""
    read = load_project(project_yaml)
    if not read.is_valid or read.paths is None:
        raise ValueError(f"invalid project: {project_yaml}")
    reason_counts: Counter[str] = Counter()
    run_root = read.paths.runs / "chapter_production"
    for path in sorted(run_root.glob("*/*/stop_requested.yaml")) if run_root.is_dir() else []:
        stop = _read_stop_artifact(path)
        if stop is None or stop.get("source") != "budget":
            continue
        reason = stop.get("reason")
        reason_counts[_budget_stop_code(reason)] += 1
    return ProductionBudgetStopMetrics(
        total_stops=sum(reason_counts.values()),
        reason_counts=dict(sorted(reason_counts.items())),
    )


def _read_stop_artifact(path: Path) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    return payload if isinstance(payload, dict) else None


def _budget_stop_code(reason: object) -> str:
    return _BUDGET_STOP_TAXONOMY.get(reason, "other_budget_policy")


def render_production_runbook_snapshot(metrics: ProductionOperationalMetrics) -> str:
    """Render a compact, path-free operational summary suitable for an incident ticket."""
    queue = metrics.queue
    fields = [
        ("queue_total_jobs", queue.total_jobs),
        ("queue_queued_jobs", queue.queued_jobs),
        ("queue_leased_jobs", queue.leased_jobs),
        ("queue_failed_jobs", queue.failed_jobs),
        ("queue_retry_count", queue.retry_count),
        ("queue_delivery_duration_count", queue.delivery_duration_count),
        ("queue_delivery_duration_total_ms", queue.delivery_duration_total_ms),
        ("queue_delivery_duration_max_ms", queue.delivery_duration_max_ms),
        ("budget_stop_total", metrics.budget_stops.total_stops),
        ("budget_stop_reason_counts", metrics.budget_stops.reason_counts),
    ]
    if metrics.admission is not None:
        fields.extend(
            [
                ("admission_active", metrics.admission.active_admissions),
                ("admission_reserved_usd", metrics.admission.reserved_usd),
            ]
        )
    return "\n".join(f"{key}={value}" for key, value in fields)


__all__ = [
    "ProductionBudgetStopMetrics",
    "ProductionOperationalMetrics",
    "collect_production_budget_stop_metrics",
    "collect_production_operational_metrics",
    "render_production_runbook_snapshot",
]
