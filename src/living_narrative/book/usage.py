"""Reader-safe actual usage attribution from durable chapter draft run artifacts."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from living_narrative.book.cost_policy import CostPriceSnapshot, CostTokenEstimate
from living_narrative.llm.metadata import CallMetadata
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project


class UsageScopeTotal(BaseModel):
    """Actual durable usage grouped by a reader-safe production scope."""

    scope_id: str
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    actual_usd: Decimal | None = None
    estimated_usd: Decimal | None = None
    variance_usd: Decimal | None = None


class UsageStageTotal(UsageScopeTotal):
    """Actual durable usage grouped by the production stage that created it."""

    stage: str


class UsageRunTotal(UsageScopeTotal):
    """Actual durable usage tied to one immutable chapter-draft attempt."""

    run_id: str
    chapter_id: str
    attempt: int = Field(ge=1)


class BookUsageSummary(BaseModel):
    """Read-only actual usage grouped for cost reporting and policy preflight."""

    book: UsageScopeTotal
    by_chapter: list[UsageScopeTotal] = Field(default_factory=list)
    by_act: list[UsageScopeTotal] = Field(default_factory=list)
    by_stage: list[UsageStageTotal] = Field(default_factory=list)
    by_run: list[UsageRunTotal] = Field(default_factory=list)
    unattributed_run_ids: list[str] = Field(default_factory=list)


class _StoredCalls(BaseModel):
    calls: list[CallMetadata] = Field(default_factory=list)


class _StoredRequest(BaseModel):
    run_id: str
    chapter_id: str
    attempt: int = Field(ge=1)


class _StoredCostAssessment(BaseModel):
    estimate_usd: Decimal | None = None


class _UsageAccumulator:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.actual_usd = Decimal(0)
        self.cost_known = True
        self.estimated_usd = Decimal(0)
        self.estimate_seen = False
        self.estimate_known = True

    def add(self, call: CallMetadata, price_snapshot: CostPriceSnapshot) -> None:
        self.calls += call.request_count
        self.prompt_tokens += call.prompt_tokens or 0
        self.completion_tokens += call.completion_tokens or 0
        self.total_tokens += call.total_tokens or (call.prompt_tokens or 0) + (
            call.completion_tokens or 0
        )
        if call.prompt_tokens is None or call.completion_tokens is None:
            self.cost_known = False
            return
        self.actual_usd += price_snapshot.estimate_usd(
            CostTokenEstimate(
                input_tokens=call.prompt_tokens,
                output_tokens=call.completion_tokens,
            )
        )

    def add_estimate(self, estimate_usd: Decimal | None) -> None:
        """Record one run-level preflight estimate without treating missing data as zero."""
        if estimate_usd is None:
            self.estimate_known = False
            return
        self.estimate_seen = True
        self.estimated_usd += estimate_usd

    def total(self, scope_id: str) -> UsageScopeTotal:
        actual_usd = self.actual_usd if self.cost_known else None
        estimated_usd = self.estimated_usd if self.estimate_seen and self.estimate_known else None
        return UsageScopeTotal(
            scope_id=scope_id,
            calls=self.calls,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            actual_usd=actual_usd,
            estimated_usd=estimated_usd,
            variance_usd=actual_usd - estimated_usd
            if actual_usd is not None and estimated_usd is not None
            else None,
        )


def _read_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def collect_book_usage(
    project_yaml: Path, *, price_snapshot: CostPriceSnapshot
) -> BookUsageSummary:
    """Attribute recorded chapter-draft usage without prompts, prose, or private state.

    Runs missing a durable request/calls contract remain listed as unattributed rather than being
    silently charged to the book total. This keeps actual spend evidence auditable.
    """
    read = load_project(project_yaml)
    if not read.is_valid or read.paths is None:
        raise ValueError(f"invalid project: {project_yaml}")
    bundle = StateStore.load(read.paths.state)
    chapter_to_act = {chapter.id: chapter.act_id for chapter in bundle.book_plan.chapters}
    book = _UsageAccumulator()
    by_chapter: defaultdict[str, _UsageAccumulator] = defaultdict(_UsageAccumulator)
    by_act: defaultdict[str, _UsageAccumulator] = defaultdict(_UsageAccumulator)
    by_stage: defaultdict[str, _UsageAccumulator] = defaultdict(_UsageAccumulator)
    by_run: list[UsageRunTotal] = []
    unattributed: list[str] = []
    drafts_root = read.paths.runs / "chapter_drafts"

    for run_dir in sorted(drafts_root.iterdir()) if drafts_root.is_dir() else []:
        if not run_dir.is_dir():
            continue
        try:
            request = _StoredRequest.model_validate(_read_yaml(run_dir / "request.yaml"))
            calls = _StoredCalls.model_validate(_read_yaml(run_dir / "calls.yaml"))
            cost_assessment = _StoredCostAssessment.model_validate(
                _read_yaml(run_dir / "cost_assessment.yaml")
            )
        except ValidationError:
            unattributed.append(run_dir.name)
            continue
        act_id = chapter_to_act.get(request.chapter_id)
        if act_id is None or not calls.calls:
            unattributed.append(run_dir.name)
            continue
        run_usage = _UsageAccumulator()
        for call in calls.calls:
            stage = call.binding_key or "draft"
            book.add(call, price_snapshot)
            by_chapter[request.chapter_id].add(call, price_snapshot)
            by_act[act_id].add(call, price_snapshot)
            by_stage[stage].add(call, price_snapshot)
            run_usage.add(call, price_snapshot)
        for accumulator in (book, by_chapter[request.chapter_id], by_act[act_id], run_usage):
            accumulator.add_estimate(cost_assessment.estimate_usd)
        by_stage["draft"].add_estimate(cost_assessment.estimate_usd)
        by_run.append(
            UsageRunTotal(
                run_id=request.run_id,
                chapter_id=request.chapter_id,
                attempt=request.attempt,
                **run_usage.total(request.run_id).model_dump(),
            )
        )

    return BookUsageSummary(
        book=book.total("book"),
        by_chapter=[by_chapter[key].total(key) for key in sorted(by_chapter)],
        by_act=[by_act[key].total(key) for key in sorted(by_act)],
        by_stage=[
            UsageStageTotal(stage=key, **by_stage[key].total(key).model_dump())
            for key in sorted(by_stage)
        ],
        by_run=by_run,
        unattributed_run_ids=unattributed,
    )
