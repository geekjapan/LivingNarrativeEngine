"""Register agent-runtime slots."""

from living_narrative.agents.character import run_character_agent
from living_narrative.agents.conflict_resolver import resolve_conflicts
from living_narrative.agents.state_manager import build_state_diff
from living_narrative.agents.world_simulator import simulate_world
from living_narrative.pipeline.registry import SlotRegistry
from living_narrative.safety.registry import run_registered_checkers


def register_agent_runtime_slots(registry: SlotRegistry) -> None:
    registry.register("simulate", simulate_world)
    registry.register("act", run_character_agent)
    registry.register("resolve", resolve_conflicts)
    registry.register("build_diff", build_state_diff)
    registry.register("check", run_registered_checkers)
