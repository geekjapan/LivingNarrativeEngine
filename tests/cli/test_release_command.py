import json

from typer.testing import CliRunner

from living_narrative.cli import app

runner = CliRunner()


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
            "narrator": {"binding": "narrator", "call_count": 30, "fallbacks": []},
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


def test_release_verify_real_llm_evidence_emits_reader_safe_json_for_valid_artifact(
    tmp_path,
):
    artifact_path = tmp_path / "benchmark.json"
    artifact_path.write_text(json.dumps(_valid_artifact()), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "release",
            "verify-real-llm-evidence",
            "--artifact",
            str(artifact_path),
            "--expected-revision",
            "a" * 40,
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "completed_turns": 30,
        "expected_revision": "a" * 40,
        "observed_revision": "a" * 40,
        "passed": True,
        "reason_codes": [],
    }
    assert "reader turn" not in result.output
    assert str(artifact_path) not in result.output


def test_release_verify_real_llm_evidence_exits_1_with_reader_safe_reason_codes(
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

    result = runner.invoke(
        app,
        [
            "release",
            "verify-real-llm-evidence",
            "--artifact",
            str(artifact_path),
            "--expected-revision",
            "a" * 40,
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "completed_turns": 30,
        "expected_revision": "a" * 40,
        "observed_revision": "a" * 40,
        "passed": False,
        "reason_codes": ["provider_failure"],
    }
    assert "TimeoutError" not in result.output
    assert "private provider response" not in result.output


def test_release_verify_real_llm_evidence_exits_2_for_missing_artifact(tmp_path):
    missing_artifact = tmp_path / "missing.json"

    result = runner.invoke(
        app,
        [
            "release",
            "verify-real-llm-evidence",
            "--artifact",
            str(missing_artifact),
            "--expected-revision",
            "a" * 40,
        ],
    )

    assert result.exit_code == 2
    assert "Error: artifact not found:" in result.output
    assert "reader turn" not in result.output
