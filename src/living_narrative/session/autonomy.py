"""Autonomy-level semantics and mode/level normalization."""

import logging
from dataclasses import dataclass
from enum import StrEnum

from living_narrative.state.models import AutonomyLevel, UserMode

logger = logging.getLogger(__name__)


class AutonomySemantics(StrEnum):
    EVERY_TURN = "every_turn"
    STOP_CONDITIONS = "stop_conditions"
    TARGET_OR_STOP_CONDITIONS = "target_or_stop_conditions"
    LIMITED_STOP_CONDITIONS = "limited_stop_conditions"


LEVEL_SEMANTICS: dict[AutonomyLevel, AutonomySemantics] = {
    AutonomyLevel.MANUAL: AutonomySemantics.EVERY_TURN,
    AutonomyLevel.ASSIST: AutonomySemantics.STOP_CONDITIONS,
    AutonomyLevel.AUTO: AutonomySemantics.TARGET_OR_STOP_CONDITIONS,
    AutonomyLevel.WATCH: AutonomySemantics.LIMITED_STOP_CONDITIONS,
    AutonomyLevel.GOD: AutonomySemantics.LIMITED_STOP_CONDITIONS,
}

LIMITED_STOP_CONDITIONS = {
    "checker_error",
    "scene_end",
    "target_turn_count_reached",
    "stop_condition",
}


@dataclass(frozen=True)
class NormalizationResult:
    user_mode: UserMode
    autonomy_level: AutonomyLevel
    normalized: bool = False
    warning: str | None = None


@dataclass(frozen=True)
class NormalizationRule:
    target_level: AutonomyLevel
    reason: str

    def matches(self, mode: UserMode, level: AutonomyLevel) -> bool:
        if mode == UserMode.WATCHER and level in {AutonomyLevel.MANUAL, AutonomyLevel.GOD}:
            return self.target_level == AutonomyLevel.WATCH
        if mode == UserMode.PLAYER_CHARACTER and level in {
            AutonomyLevel.AUTO,
            AutonomyLevel.WATCH,
            AutonomyLevel.GOD,
        }:
            return self.target_level == AutonomyLevel.ASSIST
        return False


NORMALIZATION_RULES = [
    NormalizationRule(AutonomyLevel.WATCH, "watcher mode cannot review or bypass guardrails"),
    NormalizationRule(AutonomyLevel.ASSIST, "player_character mode requires per-turn player input"),
]


def normalize_mode_level(
    user_mode: UserMode | str,
    autonomy_level: AutonomyLevel | str,
) -> NormalizationResult:
    mode = UserMode(user_mode)
    level = AutonomyLevel(autonomy_level)
    for rule in NORMALIZATION_RULES:
        if rule.matches(mode, level):
            warning = (
                f"normalized {mode.value}+{level.value} to {rule.target_level.value}: {rule.reason}"
            )
            logger.warning(warning)
            return NormalizationResult(mode, rule.target_level, True, warning)
    return NormalizationResult(mode, level)


def should_stop_for_level(autonomy_level: AutonomyLevel | str, condition_name: str) -> bool:
    level = AutonomyLevel(autonomy_level)
    if level == AutonomyLevel.MANUAL:
        return True
    if level in {AutonomyLevel.ASSIST, AutonomyLevel.AUTO}:
        return True
    return condition_name in LIMITED_STOP_CONDITIONS
