"""Auto N-turn loop wrapper around the normal TurnPipeline."""

from dataclasses import dataclass
from pathlib import Path

from living_narrative.pipeline.driver import TurnPipeline, TurnRunResult
from living_narrative.pipeline.status import TurnStatus


@dataclass(frozen=True)
class AutoLoopResult:
    turns: list[TurnRunResult]
    interrupted: bool = False


def run_auto_loop(
    project_path: Path,
    target_turn_count: int,
    pipeline: TurnPipeline | None = None,
) -> AutoLoopResult:
    pipeline = pipeline or TurnPipeline()
    turns: list[TurnRunResult] = []
    try:
        for _ in range(target_turn_count):
            result = pipeline.run(project_path)
            turns.append(result)
            if result.status != TurnStatus.APPLIED:
                break
    except KeyboardInterrupt:
        return AutoLoopResult(turns, interrupted=True)
    return AutoLoopResult(turns)
