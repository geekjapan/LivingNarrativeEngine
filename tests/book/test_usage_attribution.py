from __future__ import annotations

from decimal import Decimal

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.cost_policy import (
    CostPolicyV2,
    CostPriceSnapshot,
    CostTokenEstimate,
)
from living_narrative.book.drafting import run_chapter_draft
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.usage import collect_book_usage
from living_narrative.llm.metadata import CallMetadata
from living_narrative.workspace.init import create_project


class _Gateway:
    def __init__(self) -> None:
        self.calls = [
            CallMetadata(
                provider_name="provider-a",
                model="fiction-model",
                duration_seconds=0.2,
                prompt_template_name="book.chapter_draft.v1",
                prompt_hash="abc123",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                profile_name="fiction",
            )
        ]

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        return response_schema(body="澪は公開された時刻表の矛盾を見つけた。")


def _project(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "帳簿を調べる。",
                "audience": "fantasy readers",
                "acts": [{"id": "act_001", "promise": "調査", "chapter_ids": ["chapter_001"]}],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "矛盾を見つける。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml


def test_usage_attribution_groups_durable_draft_calls_by_chapter_act_and_book(tmp_path):
    project_yaml = _project(tmp_path)
    run_chapter_draft(project_yaml, "chapter_001", gateway=_Gateway())
    price = CostPriceSnapshot(
        profile_id="provider-a/fiction",
        version="2026-08-21",
        input_usd_per_1m=Decimal("1.50"),
        output_usd_per_1m=Decimal("6.00"),
        tax_rate=Decimal("0.00"),
        discount_rate=Decimal("0.00"),
    )

    summary = collect_book_usage(project_yaml, price_snapshot=price)

    assert summary.book.calls == 1
    assert summary.book.total_tokens == 150
    assert summary.book.actual_usd == Decimal("0.000450")
    assert summary.by_chapter[0].scope_id == "chapter_001"
    assert summary.by_chapter[0].actual_usd == Decimal("0.000450")
    assert summary.by_act[0].scope_id == "act_001"
    assert summary.by_stage[0].stage == "draft"
    assert summary.by_run[0].chapter_id == "chapter_001"
    assert summary.by_run[0].attempt == 1
    assert summary.by_run[0].actual_usd == Decimal("0.000450")
    assert summary.unattributed_run_ids == []


def test_usage_attribution_reports_estimate_actual_variance_by_run_and_book(tmp_path):
    project_yaml = _project(tmp_path)
    price = CostPriceSnapshot(
        profile_id="provider-a/fiction",
        version="2026-08-21",
        input_usd_per_1m=Decimal("1.50"),
        output_usd_per_1m=Decimal("6.00"),
        tax_rate=Decimal("0.00"),
        discount_rate=Decimal("0.00"),
    )
    run_chapter_draft(
        project_yaml,
        "chapter_001",
        gateway=_Gateway(),
        cost_policy=CostPolicyV2(price_snapshot=price),
        cost_estimate=CostTokenEstimate(input_tokens=2_000, output_tokens=1_000),
    )

    summary = collect_book_usage(project_yaml, price_snapshot=price)

    assert summary.book.estimated_usd == Decimal("0.009")
    assert summary.book.actual_usd == Decimal("0.000450")
    assert summary.book.variance_usd == Decimal("-0.008550")
    assert summary.by_run[0].estimated_usd == Decimal("0.009")
    assert summary.by_run[0].variance_usd == Decimal("-0.008550")


def test_usage_attribution_reports_incomplete_run_without_charging_it_to_book(tmp_path):
    project_yaml = _project(tmp_path)
    price = CostPriceSnapshot(
        profile_id="provider-a/fiction",
        version="2026-08-21",
        input_usd_per_1m=Decimal("1.50"),
        output_usd_per_1m=Decimal("6.00"),
        tax_rate=Decimal("0.00"),
        discount_rate=Decimal("0.00"),
    )
    incomplete = project_yaml.parent / "workspace" / "runs" / "chapter_drafts" / "orphan_run"
    incomplete.mkdir(parents=True)

    summary = collect_book_usage(project_yaml, price_snapshot=price)

    assert summary.book.calls == 0
    assert summary.book.actual_usd == Decimal("0")
    assert summary.unattributed_run_ids == ["orphan_run"]


def test_usage_attribution_keeps_actual_usd_unknown_for_partial_provider_usage(tmp_path):
    class _PartialUsageGateway(_Gateway):
        def __init__(self) -> None:
            self.calls = [
                CallMetadata(
                    provider_name="provider-a",
                    model="fiction-model",
                    duration_seconds=0.2,
                    prompt_template_name="book.chapter_draft.v1",
                    prompt_hash="partial",
                    prompt_tokens=100,
                    completion_tokens=None,
                    total_tokens=100,
                    profile_name="fiction",
                )
            ]

    project_yaml = _project(tmp_path)
    run_chapter_draft(project_yaml, "chapter_001", gateway=_PartialUsageGateway())
    price = CostPriceSnapshot(
        profile_id="provider-a/fiction",
        version="2026-08-21",
        input_usd_per_1m=Decimal("1.50"),
        output_usd_per_1m=Decimal("6.00"),
        tax_rate=Decimal("0.00"),
        discount_rate=Decimal("0.00"),
    )

    summary = collect_book_usage(project_yaml, price_snapshot=price)

    assert summary.book.total_tokens == 100
    assert summary.book.actual_usd is None
    assert summary.by_chapter[0].actual_usd is None
    assert summary.unattributed_run_ids == []
