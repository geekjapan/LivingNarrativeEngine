"""Dictionary-based checker registry."""

from collections.abc import Callable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import CheckResult
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event

Severity = Literal["info", "warn", "error"]
Checker = Callable[[TurnContext, str, list[Event], StateDiff], list["Finding"]]
CHECKERS: dict[str, Checker] = {}


class Finding(BaseModel):
    checker: str
    severity: Severity
    message: str
    related_ids: list[str] = Field(default_factory=list)


class CheckRunResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    blocks_auto_apply: bool = False


def register_checker(name: str, checker: Checker) -> None:
    CHECKERS[name] = checker


def run_checkers(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
    *,
    names: list[str] | None = None,
) -> CheckRunResult:
    selected = names or list(CHECKERS)
    findings: list[Finding] = []
    for name in selected:
        findings.extend(CHECKERS[name](context, narration_text, resolved_events, diff_candidate))
    return CheckRunResult(
        findings=findings,
        blocks_auto_apply=any(finding.severity == "error" for finding in findings),
    )


def run_registered_checkers(
    context: TurnContext,
    narration_text: str,
    resolved_events: list[Event],
    diff_candidate: StateDiff,
) -> list[CheckResult]:
    result = run_checkers(context, narration_text, resolved_events, diff_candidate)
    return [
        CheckResult(
            severity=finding.severity,
            message=finding.message,
            source=finding.checker,
            related_ids=finding.related_ids,
        )
        for finding in result.findings
    ]


def write_checks_yaml(path: Path, result: CheckRunResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"findings": [finding.model_dump(mode="json") for finding in result.findings]},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _install_defaults() -> None:
    from living_narrative.safety.continuity_check import continuity_checker
    from living_narrative.safety.leak_check import leak_checker
    from living_narrative.safety.pacing_check import pacing_checker
    from living_narrative.safety.speech_check import speech_register_checker

    register_checker("leak", leak_checker)
    register_checker("continuity", continuity_checker)
    register_checker("pacing", pacing_checker)
    register_checker("speech", speech_register_checker)


_install_defaults()
