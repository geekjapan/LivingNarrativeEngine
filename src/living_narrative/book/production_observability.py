"""Reader-safe operational projection for durable chapter production."""

from __future__ import annotations

from pathlib import Path

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


class ProductionOperationalMetrics(BaseModel):
    """Read-only operations view that intentionally contains no book content."""

    queue: ProductionQueueMetrics
    admission: ProductionAdmissionMetrics | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


def collect_production_operational_metrics(project_yaml: Path) -> ProductionOperationalMetrics:
    """Collect the public durable-delivery health projection without state mutation."""
    configured = load_project_production_admission(project_yaml)
    return ProductionOperationalMetrics(
        queue=collect_production_queue_metrics(project_yaml),
        admission=(
            collect_production_admission_metrics(configured.scheduler_root)
            if configured is not None
            else None
        ),
    )


def render_production_runbook_snapshot(metrics: ProductionOperationalMetrics) -> str:
    """Render a compact, path-free operational summary suitable for an incident ticket."""
    queue = metrics.queue
    fields = [
        ("queue_total_jobs", queue.total_jobs),
        ("queue_queued_jobs", queue.queued_jobs),
        ("queue_leased_jobs", queue.leased_jobs),
        ("queue_failed_jobs", queue.failed_jobs),
        ("queue_retry_count", queue.retry_count),
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
    "ProductionOperationalMetrics",
    "collect_production_operational_metrics",
    "render_production_runbook_snapshot",
]
