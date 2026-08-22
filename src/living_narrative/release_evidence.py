"""Reader-safe validation for real-LLM release evidence artifacts."""

from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

_FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "credentials",
        "gm_vault",
        "hidden_facts",
        "private_mind",
        "prompt",
        "prompts",
        "traceback",
    }
)


def _contains_forbidden_evidence_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold() in _FORBIDDEN_EVIDENCE_KEYS
            or _contains_forbidden_evidence_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_evidence_key(item) for item in value)
    return False


def _has_unsafe_source_reference(payload: dict[object, object]) -> bool:
    sources = payload.get("sources")
    return isinstance(sources, dict) and any(
        isinstance(value, str)
        and (Path(value).is_absolute() or PureWindowsPath(value).is_absolute())
        for value in sources.values()
    )


def _has_credentialed_provider_url(run: dict[object, object]) -> bool:
    base_url = run.get("base_url")
    if not isinstance(base_url, str):
        return False
    parsed = urlsplit(base_url)
    return parsed.username is not None or parsed.password is not None or bool(parsed.query)


class RealLLMBenchmarkValidation(BaseModel):
    """A path-free validation result safe to include in release evidence."""

    passed: bool
    reason_codes: tuple[str, ...] = ()
    completed_turns: int = Field(ge=0)
    expected_revision: str
    observed_revision: str | None = None


def validate_real_llm_benchmark_artifact(
    path: Path,
    expected_revision: str,
) -> RealLLMBenchmarkValidation:
    """Validate the machine-checkable contract of a real-LLM benchmark artifact.

    The validator is read-only and deliberately returns only stable reason codes and
    revision/count metadata. It never copies narration or other artifact content into
    its result.
    """
    reason_codes: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = None
        reason_codes.append("invalid_artifact")

    if not isinstance(payload, dict):
        return RealLLMBenchmarkValidation(
            passed=False,
            reason_codes=tuple(reason_codes or ["invalid_artifact"]),
            completed_turns=0,
            expected_revision=expected_revision,
        )

    if payload.get("schema_version") != 1:
        reason_codes.append("unsupported_schema")
    if payload.get("artifact_type") != "real_llm_benchmark":
        reason_codes.append("invalid_artifact_type")

    run = payload.get("run")
    if not isinstance(run, dict):
        run = {}
        reason_codes.append("invalid_run")
    observed_revision = run.get("git_revision")
    if not isinstance(observed_revision, str):
        observed_revision = None
        reason_codes.append("missing_revision")
    elif observed_revision != expected_revision:
        reason_codes.append("revision_mismatch")

    completed_turns = run.get("completed_turns")
    if not isinstance(completed_turns, int) or completed_turns < 0:
        completed_turns = 0
        reason_codes.append("invalid_completed_turns")
    turns = payload.get("turns")
    turns_are_complete = isinstance(turns, list) and [
        (turn.get("turn"), turn.get("status")) for turn in turns if isinstance(turn, dict)
    ] == [(turn, "applied") for turn in range(1, 31)]
    if (
        run.get("status") != "PASS"
        or run.get("target_turns") != 30
        or completed_turns != 30
        or not turns_are_complete
    ):
        reason_codes.append("incomplete_turns")
    if run.get("provider_failures"):
        reason_codes.append("provider_failure")

    mechanical = payload.get("mechanical")
    narrator = mechanical.get("narrator") if isinstance(mechanical, dict) else None
    if not isinstance(narrator, dict) or narrator.get("fallbacks"):
        reason_codes.append("narrator_fallback")
    elif not isinstance(narrator.get("call_count"), int) or narrator["call_count"] <= 0:
        reason_codes.append("narrator_not_confirmed")
    resume = mechanical.get("resume") if isinstance(mechanical, dict) else None
    if (
        not isinstance(resume, dict)
        or resume.get("status") != "PASS"
        or resume.get("checkpoint_turn") != 15
        or resume.get("resumed_at_turn") != 16
    ):
        reason_codes.append("resume_not_confirmed")
    leak_scan = mechanical.get("leak_scan") if isinstance(mechanical, dict) else None
    if (
        not isinstance(leak_scan, dict)
        or leak_scan.get("status") != "PASS"
        or leak_scan.get("findings")
    ):
        reason_codes.append("leak_scan_not_passed")
    if _contains_forbidden_evidence_key(payload) or _has_credentialed_provider_url(run):
        reason_codes.append("private_evidence")
    if _has_unsafe_source_reference(payload):
        reason_codes.append("unsafe_reference")

    return RealLLMBenchmarkValidation(
        passed=not reason_codes,
        reason_codes=tuple(reason_codes),
        completed_turns=completed_turns,
        expected_revision=expected_revision,
        observed_revision=observed_revision,
    )


__all__ = ["RealLLMBenchmarkValidation", "validate_real_llm_benchmark_artifact"]
