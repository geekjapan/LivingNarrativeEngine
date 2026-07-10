from pathlib import Path

import yaml

from living_narrative.llm.costs import BUILTIN_MODEL_PRICING, collect_project_costs


def _write_meta(runs_dir: Path, directory: str, data: dict) -> None:
    turn_dir = runs_dir / directory
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _call(
    model: str,
    *,
    prompt: int = 10,
    completion: int = 20,
    profile: str | None = "main",
    request_count: int = 1,
) -> dict:
    return {
        "provider_name": "test",
        "model": model,
        "duration_seconds": 0.1,
        "prompt_template_name": "test",
        "prompt_hash": "hash",
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "profile_name": profile,
        "request_count": request_count,
    }


def test_collect_project_costs_groups_models_and_profiles(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.touch()
    runs_dir = tmp_path / "workspace" / "runs"
    _write_meta(
        runs_dir,
        "turn_0001",
        {
            "llm_tokens_total": 35,
            "llm_calls": [
                _call("known", request_count=2),
                _call("unknown", prompt=2, completion=3, profile=None),
            ],
        },
    )
    (tmp_path / "pricing.yaml").write_text(
        yaml.safe_dump({"known": {"input_usd_per_1m": 1.0, "output_usd_per_1m": 2.0}}),
        encoding="utf-8",
    )

    usage = collect_project_costs(project_path, runs_dir)

    assert usage.calls == 3
    assert usage.prompt_tokens == 12
    assert usage.completion_tokens == 23
    assert usage.total_tokens == 35
    assert usage.cost_usd is None
    assert usage.unpriced_models == ["unknown"]
    assert [(entry.model, entry.cost_usd) for entry in usage.by_model] == [
        ("known", 0.00005),
        ("unknown", None),
    ]
    assert [(entry.profile_name, entry.calls) for entry in usage.by_profile] == [
        ("main", 2),
        (None, 1),
    ]


def test_collect_project_costs_excludes_non_live_and_invalid_turns(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.touch()
    runs_dir = tmp_path / "runs"
    _write_meta(runs_dir, "turn_0001", {"llm_tokens_total": 30, "llm_calls": [_call("m")]})
    _write_meta(
        runs_dir,
        "turn_0001_discarded_1",
        {"llm_tokens_total": 30, "llm_calls": [_call("discarded")]},
    )
    _write_meta(
        runs_dir,
        "turn_0002_rolledback_1",
        {"llm_tokens_total": 30, "llm_calls": [_call("rolledback")]},
    )
    malformed = runs_dir / "turn_0002"
    malformed.mkdir()
    (malformed / "meta.yaml").write_text("llm_calls: [", encoding="utf-8")
    (runs_dir / "turn_0003").mkdir()
    _write_meta(runs_dir, "turn_0004", {"llm_calls": [{"model": "incomplete"}]})
    _write_meta(runs_dir, "turn_0005", {"llm_tokens_total": 99})

    usage = collect_project_costs(project_path, runs_dir)

    assert usage.calls == 1
    assert usage.total_tokens == 30
    assert [entry.model for entry in usage.by_model] == ["m"]


def test_missing_or_invalid_pricing_keeps_usage_and_returns_unknown_cost(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.touch()
    runs_dir = tmp_path / "runs"
    _write_meta(runs_dir, "turn_0001", {"llm_tokens_total": 30, "llm_calls": [_call("m")]})

    assert BUILTIN_MODEL_PRICING == {}
    missing = collect_project_costs(project_path, runs_dir)
    assert missing.calls == 1
    assert missing.cost_usd is None

    (tmp_path / "pricing.yaml").write_text("m: [not-a-price]", encoding="utf-8")
    invalid = collect_project_costs(project_path, runs_dir)
    assert invalid.calls == 1
    assert invalid.cost_usd is None


def test_pricing_requires_exact_model_name(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.touch()
    runs_dir = tmp_path / "runs"
    _write_meta(
        runs_dir,
        "turn_0001",
        {"llm_tokens_total": 30, "llm_calls": [_call("vendor/model-v2")]},
    )
    (tmp_path / "pricing.yaml").write_text(
        yaml.safe_dump({"vendor/model": {"input_usd_per_1m": 1.0, "output_usd_per_1m": 1.0}}),
        encoding="utf-8",
    )

    usage = collect_project_costs(project_path, runs_dir)

    assert usage.cost_usd is None
    assert usage.unpriced_models == ["vendor/model-v2"]
