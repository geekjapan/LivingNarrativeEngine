"""Deterministic, reader-safe token/USD budget evaluation for book production."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class CostScope(StrEnum):
    """The production level whose cost is being evaluated."""

    CHAPTER = "chapter"
    ACT = "act"
    BOOK = "book"


class CostPolicyStatus(StrEnum):
    """The preflight decision that a caller may project without provider details."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    UNKNOWN = "unknown"


class CostPriceSnapshot(BaseModel):
    """Immutable USD pricing for one configured provider profile version."""

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    input_usd_per_1m: Decimal = Field(ge=0)
    output_usd_per_1m: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, lt=1)
    discount_rate: Decimal = Field(ge=0, lt=1)

    def estimate_usd(self, estimate: CostTokenEstimate) -> Decimal:
        """Return the tax-and-discount-inclusive USD estimate without display rounding."""
        subtotal = (
            Decimal(estimate.input_tokens) * self.input_usd_per_1m
            + Decimal(estimate.output_tokens) * self.output_usd_per_1m
        ) / Decimal(1_000_000)
        return subtotal * (Decimal(1) + self.tax_rate) * (Decimal(1) - self.discount_rate)


class CostScopeBudget(BaseModel):
    """Optional soft and hard USD caps for one production scope."""

    soft_usd: Decimal | None = Field(default=None, ge=0)
    hard_usd: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_cap_order(self) -> CostScopeBudget:
        """Reject an inverted threshold rather than silently weakening the hard cap."""
        if (
            self.soft_usd is not None
            and self.hard_usd is not None
            and self.soft_usd > self.hard_usd
        ):
            raise ValueError("soft_usd must not exceed hard_usd")
        return self


class CostPolicyV2(BaseModel):
    """A price snapshot and independent budgets evaluated before provider invocation."""

    price_snapshot: CostPriceSnapshot | None = None
    budgets: dict[CostScope, CostScopeBudget] = Field(default_factory=dict)


class CostTokenEstimate(BaseModel):
    """Known token counts required for a preflight cost calculation."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class CostPolicyAssessment(BaseModel):
    """Reader-safe result of a deterministic cost-policy preflight."""

    status: CostPolicyStatus
    scope: CostScope
    estimate_usd: Decimal | None
    spent_usd: Decimal | None
    forecast_usd: Decimal | None
    price_version: str | None
    reason: str | None = None


def evaluate_cost_policy(
    policy: CostPolicyV2,
    *,
    scope: CostScope,
    spent_usd: Decimal | None,
    estimate: CostTokenEstimate | None,
) -> CostPolicyAssessment:
    """Evaluate one scope without state mutation or a provider call.

    A scope without a cap is permitted. The stricter unknown-value policy is added when a hard
    cap exists, so callers cannot accidentally treat an unknown quote as free spend.
    """
    budget = policy.budgets.get(scope)
    if policy.price_snapshot is None or estimate is None or spent_usd is None:
        status = (
            CostPolicyStatus.BLOCK
            if budget is not None and budget.hard_usd is not None
            else CostPolicyStatus.UNKNOWN
        )
        return CostPolicyAssessment(
            status=status,
            scope=scope,
            estimate_usd=None,
            spent_usd=spent_usd,
            forecast_usd=None,
            price_version=policy.price_snapshot.version if policy.price_snapshot else None,
            reason=f"{scope.value} USD budget cannot be evaluated",
        )

    estimate_usd = policy.price_snapshot.estimate_usd(estimate)
    forecast_usd = spent_usd + estimate_usd
    if budget is None:
        status = CostPolicyStatus.ALLOW
        reason = None
    elif budget.hard_usd is not None and forecast_usd > budget.hard_usd:
        status = CostPolicyStatus.BLOCK
        reason = f"{scope.value} hard USD budget exceeded"
    elif budget.soft_usd is not None and forecast_usd > budget.soft_usd:
        status = CostPolicyStatus.WARN
        reason = f"{scope.value} soft USD budget exceeded"
    else:
        status = CostPolicyStatus.ALLOW
        reason = None
    return CostPolicyAssessment(
        status=status,
        scope=scope,
        estimate_usd=estimate_usd,
        spent_usd=spent_usd,
        forecast_usd=forecast_usd,
        price_version=policy.price_snapshot.version,
        reason=reason,
    )
