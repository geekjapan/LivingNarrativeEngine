import json

from living_narrative.release_evidence import validate_real_llm_benchmark_artifact


def _valid_artifact(revision: str = "a" * 40) -> dict[str, object]:
    return {
        "schema_version": 1,
        "artifact_type": "real_llm_benchmark",
        "run": {
            "run_id": "rc-gate-001",
            "gate": "1.0",
            "git_revision": revision,
            "target_turns": 30,
            "completed_turns": 30,
            "status": "PASS",
            "provider_failures": [],
        },
        "turns": [
            {"turn": turn, "status": "applied", "narration": f"reader turn {turn}"}
            for turn in range(1, 31)
        ],
        "mechanical": {
            "narrator": {
                "binding": "narrator",
                "call_count": 30,
                "fallbacks": [],
            },
            "leak_scan": {"status": "PASS", "findings": []},
            "resume": {
                "status": "PASS",
                "checkpoint_turn": 15,
                "resumed_at_turn": 16,
            },
        },
        "sources": {
            "run_artifacts": "sandbox/rc-gate-001/workspace/runs",
            "metrics_json": "sandbox/rc-gate-001/metrics.json",
            "benchmark_markdown": "docs/evaluations/rc-gate-001-benchmark.md",
        },
    }


def test_validate_real_llm_benchmark_artifact_accepts_complete_reader_safe_evidence(
    tmp_path,
):
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(_valid_artifact()), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is True
    assert validation.reason_codes == ()
    assert validation.completed_turns == 30
    assert validation.expected_revision == "a" * 40
    assert validation.observed_revision == "a" * 40
    assert "reader turn" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_a_different_release_revision(
    tmp_path,
):
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(_valid_artifact(revision="b" * 40)), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("revision_mismatch",)
    assert validation.observed_revision == "b" * 40
    assert "reader turn" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_provider_failure_without_detail(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["run"]["provider_failures"] = [
        {
            "turn": 17,
            "phase": "narrate",
            "exception_type": "TimeoutError",
            "reason": "private provider response must not be rendered",
        }
    ]
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("provider_failure",)
    assert "TimeoutError" not in validation.model_dump_json()
    assert "private provider response" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_missing_or_non_applied_turns(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["turns"][18]["status"] = "failed"
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("incomplete_turns",)


def test_validate_real_llm_benchmark_artifact_rejects_narrator_fallback_without_detail(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["mechanical"]["narrator"]["fallbacks"] = [
        {"turn": 9, "reason": "private provider detail"}
    ]
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("narrator_fallback",)
    assert "private provider detail" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_private_context_without_echoing_it(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["turns"][0]["gm_vault"] = {"hidden_fact": "do not disclose"}
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("private_evidence",)
    assert "hidden_fact" not in validation.model_dump_json()
    assert "do not disclose" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_missing_resume_confirmation(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["mechanical"]["resume"]["status"] = "FAIL"
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("resume_not_confirmed",)


def test_validate_real_llm_benchmark_artifact_rejects_failed_leak_scan_without_detail(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["mechanical"]["leak_scan"] = {
        "status": "FAIL",
        "findings": [{"severity": "critical", "detail": "private hidden content"}],
    }
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("leak_scan_not_passed",)
    assert "private hidden content" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_absolute_source_path_without_echoing_it(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["sources"]["metrics_json"] = "/private/var/folders/secret/metrics.json"
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("unsafe_reference",)
    assert "/private/var" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_rejects_credentialed_provider_url(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["run"]["base_url"] = "https://token:private-secret@example.test/v1"
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("private_evidence",)
    assert "private-secret" not in validation.model_dump_json()


def test_validate_real_llm_benchmark_artifact_is_read_only(tmp_path):
    artifact_path = tmp_path / "benchmark.json"
    rendered = json.dumps(_valid_artifact(), ensure_ascii=False, indent=2)
    artifact_path.write_text(rendered, encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is True
    assert artifact_path.read_text(encoding="utf-8") == rendered


def test_validate_real_llm_benchmark_artifact_rejects_missing_narrator_calls(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["mechanical"]["narrator"]["call_count"] = 0
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("narrator_not_confirmed",)


def test_validate_real_llm_benchmark_artifact_rejects_windows_absolute_source_path(
    tmp_path,
):
    artifact = _valid_artifact()
    artifact["sources"]["metrics_json"] = "C:\\Users\\release\\metrics.json"
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    validation = validate_real_llm_benchmark_artifact(artifact_path, expected_revision="a" * 40)

    assert validation.passed is False
    assert validation.reason_codes == ("unsafe_reference",)
    assert "C:\\Users" not in validation.model_dump_json()
