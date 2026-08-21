from __future__ import annotations

from decimal import Decimal

from living_narrative.book.cost_policy import (
    CostPolicyStatus,
    CostPolicyV2,
    CostPriceSnapshot,
    CostScope,
    CostScopeBudget,
    CostTokenEstimate,
    evaluate_cost_policy,
)


def test_cost_policy_uses_versioned_decimal_price_snapshot_for_soft_cap_warning():
    policy = CostPolicyV2(
        price_snapshot=CostPriceSnapshot(
            profile_id="provider-a/fiction",
            version="2026-08-21",
            input_usd_per_1m=Decimal("1.50"),
            output_usd_per_1m=Decimal("6.00"),
            tax_rate=Decimal("0.10"),
            discount_rate=Decimal("0.00"),
        ),
        budgets={
            CostScope.CHAPTER: CostScopeBudget(
                soft_usd=Decimal("0.010"),
                hard_usd=Decimal("0.020"),
            )
        },
    )

    assessment = evaluate_cost_policy(
        policy,
        scope=CostScope.CHAPTER,
        spent_usd=Decimal("0.001"),
        estimate=CostTokenEstimate(input_tokens=2_000, output_tokens=1_000),
    )

    assert assessment.status is CostPolicyStatus.WARN
    assert assessment.estimate_usd == Decimal("0.00990")
    assert assessment.forecast_usd == Decimal("0.01090")
    assert assessment.price_version == "2026-08-21"
    assert assessment.reason == "chapter soft USD budget exceeded"


def test_cost_policy_blocks_unknown_estimate_when_a_hard_cap_exists():
    policy = CostPolicyV2(
        price_snapshot=CostPriceSnapshot(
            profile_id="provider-a/fiction",
            version="2026-08-21",
            input_usd_per_1m=Decimal("1.50"),
            output_usd_per_1m=Decimal("6.00"),
            tax_rate=Decimal("0.00"),
            discount_rate=Decimal("0.00"),
        ),
        budgets={CostScope.BOOK: CostScopeBudget(hard_usd=Decimal("5.00"))},
    )

    assessment = evaluate_cost_policy(
        policy,
        scope=CostScope.BOOK,
        spent_usd=Decimal("1.00"),
        estimate=None,
    )

    assert assessment.status is CostPolicyStatus.BLOCK
    assert assessment.estimate_usd is None
    assert assessment.forecast_usd is None
    assert assessment.reason == "book USD budget cannot be evaluated"


def test_cost_policy_blocks_unpriced_profile_when_a_hard_cap_exists():
    policy = CostPolicyV2(
        price_snapshot=None,
        budgets={CostScope.ACT: CostScopeBudget(hard_usd=Decimal("2.00"))},
    )

    assessment = evaluate_cost_policy(
        policy,
        scope=CostScope.ACT,
        spent_usd=Decimal("0.50"),
        estimate=CostTokenEstimate(input_tokens=2_000, output_tokens=1_000),
    )

    assert assessment.status is CostPolicyStatus.BLOCK
    assert assessment.price_version is None
    assert assessment.reason == "act USD budget cannot be evaluated"


def test_cost_scope_budget_rejects_a_soft_cap_above_hard_cap():
    import pytest

    with pytest.raises(ValueError, match="soft_usd must not exceed hard_usd"):
        CostScopeBudget(soft_usd=Decimal("2.01"), hard_usd=Decimal("2.00"))
