"""Mechanical stop-condition evaluation at the Check -> Commit boundary."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from living_narrative.random.models import Roll
from living_narrative.session.autonomy import should_stop_for_level
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import AutonomyLevel, ProjectConfig


class StopConditionName(StrEnum):
    CHARACTER_DEATH = "character_death"
    MAJOR_CANON_CHANGE = "major_canon_change"
    RELATIONSHIP_THRESHOLD_CROSSING = "relationship_threshold_crossing"
    MAJOR_SECRET_REVEAL = "major_secret_reveal"
    CHECKER_ERROR = "checker_error"
    LEAK_SUSPICION = "leak_suspicion"
    HEAVY_ROLL_FAILURE = "heavy_roll_failure"
    SCENE_END = "scene_end"
    TARGET_TURN_COUNT_REACHED = "target_turn_count_reached"
    STOP_CONDITION = "stop_condition"


@dataclass(frozen=True)
class StopConditionResult:
    name: StopConditionName
    should_stop: bool
    log_only: bool = False


def _enabled(project: ProjectConfig, name: StopConditionName) -> bool:
    if name == StopConditionName.STOP_CONDITION:
        return True
    config = project.stop_conditions.get(name.value)
    return True if config is None else config.enabled


def _threshold(project: ProjectConfig, name: StopConditionName, default: int = 20) -> int:
    config = project.stop_conditions.get(name.value)
    return default if config is None or config.threshold is None else config.threshold


def _has_status_set(diff: StateDiff, target: str, value: str) -> bool:
    return any(
        change.target == target
        and change.op == "set"
        and change.path == "status"
        and change.value == value
        for change in diff.changes
    )


def _has_relationship_threshold_crossing(diff: StateDiff, threshold: int) -> bool:
    return any(
        change.target == "relationship"
        and change.op == "delta"
        and isinstance(change.value, int)
        and abs(change.value) >= threshold
        for change in diff.changes
    )


def _has_major_secret_reveal(diff: StateDiff) -> bool:
    return any(
        change.target in {"gm_vault", "character"} and change.visibility == "reader"
        for change in diff.changes
    )


def _has_major_canon_change(diff: StateDiff) -> bool:
    return any(
        change.target == "canon"
        and isinstance(change.value, dict)
        and change.value.get("severity") == "major"
        for change in diff.changes
    )


def _has_heavy_roll_failure(rolls: list[Roll]) -> bool:
    return any(roll.severity == "critical" and roll.outcome == "failure" for roll in rolls)


def _has_stop_condition(interventions: list[dict[str, Any]]) -> bool:
    return any(item.get("type") == "stop_condition" for item in interventions)


def evaluate_stop_conditions(
    *,
    project: ProjectConfig,
    autonomy_level: AutonomyLevel | str,
    diff: StateDiff,
    checks: list[Any],
    rolls: list[Roll] | None = None,
    interventions: list[dict[str, Any]] | None = None,
    target_turn_count: int | None = None,
    completed_turns: int | None = None,
) -> list[StopConditionResult]:
    rolls = rolls or []
    interventions = interventions or []
    facts = {
        StopConditionName.CHARACTER_DEATH: _has_status_set(diff, "character", "dead"),
        StopConditionName.MAJOR_CANON_CHANGE: _has_major_canon_change(diff),
        StopConditionName.RELATIONSHIP_THRESHOLD_CROSSING: _has_relationship_threshold_crossing(
            diff, _threshold(project, StopConditionName.RELATIONSHIP_THRESHOLD_CROSSING)
        ),
        StopConditionName.MAJOR_SECRET_REVEAL: _has_major_secret_reveal(diff),
        StopConditionName.CHECKER_ERROR: any(check.severity == "error" for check in checks),
        StopConditionName.LEAK_SUSPICION: any(
            check.severity in {"warn", "error"} and check.source == "leak_check" for check in checks
        ),
        StopConditionName.HEAVY_ROLL_FAILURE: _has_heavy_roll_failure(rolls),
        StopConditionName.SCENE_END: _has_status_set(diff, "scene", "ended"),
        StopConditionName.TARGET_TURN_COUNT_REACHED: (
            target_turn_count is not None
            and completed_turns is not None
            and completed_turns >= target_turn_count
        ),
        StopConditionName.STOP_CONDITION: _has_stop_condition(interventions),
    }
    results: list[StopConditionResult] = []
    for name, matched in facts.items():
        if not matched or not _enabled(project, name):
            continue
        should_stop = should_stop_for_level(autonomy_level, name.value)
        results.append(StopConditionResult(name, should_stop, log_only=not should_stop))
    return results
