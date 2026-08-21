"""Reader-safe operational projection for durable chapter production."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from living_narrative.book.production_queue import (
    ProductionQueueMetrics,
    collect_production_queue_metrics,
)


class ProductionOperationalMetrics(BaseModel):
    """Read-only operations view that intentionally contains no book content."""

    queue: ProductionQueueMetrics


def collect_production_operational_metrics(project_yaml: Path) -> ProductionOperationalMetrics:
    """Collect the public durable-delivery health projection without state mutation."""
    return ProductionOperationalMetrics(queue=collect_production_queue_metrics(project_yaml))


def render_production_runbook_snapshot(metrics: ProductionOperationalMetrics) -> str:
    """Render a compact, path-free operational summary suitable for an incident ticket."""
    queue = metrics.queue
    fields = (
        ("queue_total_jobs", queue.total_jobs),
        ("queue_queued_jobs", queue.queued_jobs),
        ("queue_leased_jobs", queue.leased_jobs),
        ("queue_failed_jobs", queue.failed_jobs),
        ("queue_retry_count", queue.retry_count),
    )
    return "\n".join(f"{key}={value}" for key, value in fields)


__all__ = [
    "ProductionOperationalMetrics",
    "collect_production_operational_metrics",
    "render_production_runbook_snapshot",
]
