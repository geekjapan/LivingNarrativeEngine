"""Read-only LLM usage and cost aggregation from canonical turn metadata."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from living_narrative.llm.metadata import CallMetadata
from living_narrative.pipeline.turn_numbering import existing_turn_numbers, turn_dir_path


class ModelPricing(BaseModel):
    """USD prices per one million input/output tokens for one exact model name."""

    model_config = ConfigDict(extra="forbid")

    input_usd_per_1m: float = Field(ge=0)
    output_usd_per_1m: float = Field(ge=0)


BUILTIN_MODEL_PRICING: dict[str, ModelPricing] = {}
_PRICING_ADAPTER = TypeAdapter(dict[str, ModelPricing])


class UsageTotals(BaseModel):
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None


class ModelUsage(UsageTotals):
    model: str


class ProfileUsage(UsageTotals):
    profile_name: str | None


class ProjectCostSummary(UsageTotals):
    by_model: list[ModelUsage] = Field(default_factory=list)
    by_profile: list[ProfileUsage] = Field(default_factory=list)
    unpriced_models: list[str] = Field(default_factory=list)


class _TurnUsageMeta(BaseModel):
    llm_calls: list[CallMetadata]
    llm_tokens_total: int | None = Field(default=None, ge=0)


class _Accumulator:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cost = 0.0
        self.cost_known = True

    def add(self, call: CallMetadata, pricing: ModelPricing | None) -> None:
        self.calls += call.request_count
        self.prompt_tokens += call.prompt_tokens or 0
        self.completion_tokens += call.completion_tokens or 0
        if call.total_tokens is not None:
            self.total_tokens += call.total_tokens
        else:
            self.total_tokens += (call.prompt_tokens or 0) + (call.completion_tokens or 0)

        if pricing is None or call.prompt_tokens is None or call.completion_tokens is None:
            self.cost_known = False
            return
        self.cost += (
            call.prompt_tokens * pricing.input_usd_per_1m
            + call.completion_tokens * pricing.output_usd_per_1m
        ) / 1_000_000

    def totals(self) -> dict[str, int | float | None]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost if self.cost_known else None,
        }


def load_model_pricing(project_path: Path) -> dict[str, ModelPricing]:
    """Load exact-name prices from ``pricing.yaml`` beside ``project.yaml``.

    A missing or invalid file safely produces the deliberately empty built-in snapshot.
    """
    pricing_path = project_path.parent / "pricing.yaml"
    if not pricing_path.is_file():
        return dict(BUILTIN_MODEL_PRICING)
    try:
        raw = yaml.safe_load(pricing_path.read_text(encoding="utf-8")) or {}
        external = _PRICING_ADAPTER.validate_python(raw)
    except (OSError, yaml.YAMLError, ValidationError):
        return dict(BUILTIN_MODEL_PRICING)
    return {**BUILTIN_MODEL_PRICING, **external}


def _read_turn_meta(turn_dir: Path) -> _TurnUsageMeta | None:
    meta_path = turn_dir / "meta.yaml"
    if not meta_path.is_file():
        return None
    try:
        raw = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return _TurnUsageMeta.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError):
        return None


def collect_project_costs(project_path: Path, runs_dir: Path) -> ProjectCostSummary:
    """Aggregate canonical ``turn_NNNN/meta.yaml`` usage without mutating project state."""
    pricing = load_model_pricing(project_path)
    project = _Accumulator()
    models: defaultdict[str, _Accumulator] = defaultdict(_Accumulator)
    profiles: defaultdict[str | None, _Accumulator] = defaultdict(_Accumulator)
    recorded_total_tokens = 0

    for turn in existing_turn_numbers(runs_dir):
        meta = _read_turn_meta(turn_dir_path(runs_dir, turn))
        if meta is None:
            continue
        for call in meta.llm_calls:
            model_pricing = pricing.get(call.model)
            project.add(call, model_pricing)
            models[call.model].add(call, model_pricing)
            profiles[call.profile_name].add(call, model_pricing)
        recorded_total_tokens += (
            meta.llm_tokens_total
            if meta.llm_tokens_total is not None
            else sum(
                call.total_tokens
                if call.total_tokens is not None
                else (call.prompt_tokens or 0) + (call.completion_tokens or 0)
                for call in meta.llm_calls
            )
        )

    project_totals = project.totals()
    project_totals["total_tokens"] = recorded_total_tokens
    by_model = [
        ModelUsage(model=model, **accumulator.totals())
        for model, accumulator in sorted(models.items())
    ]
    by_profile = [
        ProfileUsage(profile_name=profile, **accumulator.totals())
        for profile, accumulator in sorted(
            profiles.items(), key=lambda item: (item[0] is None, item[0] or "")
        )
    ]
    return ProjectCostSummary(
        **project_totals,
        by_model=by_model,
        by_profile=by_profile,
        unpriced_models=sorted(model for model in models if model not in pricing),
    )
