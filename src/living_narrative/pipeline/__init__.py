"""8-phase turn driver, registry-swappable slots, turn artifacts (spec-foundation.md §6)."""

from typing import TYPE_CHECKING, Any

from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.errors import LoadError, UnresolvedTurnError
from living_narrative.pipeline.registry import SlotRegistry, default_registry
from living_narrative.pipeline.rng_state import total_rng_draws_consumed
from living_narrative.pipeline.status import TurnStatus
from living_narrative.pipeline.turn_numbering import (
    determine_next_turn_number,
    discard_turn_directory,
    existing_turn_numbers,
    read_turn_status,
    rollback_turn_directory,
    turn_dir_path,
)
from living_narrative.pipeline.version import PIPELINE_VERSION

if TYPE_CHECKING:
    from living_narrative.pipeline.driver import TurnPipeline, TurnRunResult


def __getattr__(name: str) -> Any:
    if name in {"TurnPipeline", "TurnRunResult"}:
        from living_narrative.pipeline import driver

        return getattr(driver, name)
    raise AttributeError(name)


__all__ = [
    "PIPELINE_VERSION",
    "LoadError",
    "SlotRegistry",
    "TurnContext",
    "TurnPipeline",
    "TurnRunResult",
    "TurnStatus",
    "UnresolvedTurnError",
    "default_registry",
    "determine_next_turn_number",
    "discard_turn_directory",
    "existing_turn_numbers",
    "read_turn_status",
    "rollback_turn_directory",
    "total_rng_draws_consumed",
    "turn_dir_path",
]
