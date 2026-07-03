import pytest
from pydantic import ValidationError

from living_narrative.agents.models import BackgroundEventCandidate
from living_narrative.agents.world_simulator import simulate_world
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import (
    LLMConfig,
    ProjectConfig,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)


def _context(seed: str = "seed") -> TurnContext:
    project = ProjectConfig(
        id="p",
        title="P",
        genre="g",
        tone="t",
        autonomy_level="auto",
        user_mode="watcher",
        random_seed=seed,
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock"),
        workspace=WorkspaceConfig(root=".", state="state", runs="runs", exports="exports"),
    )
    return TurnContext(
        turn=1,
        project=project,
        paths=None,
        bundle=WorldStateBundle(world=WorldState(id="world_001", name="World", summary="")),
        random_engine=RandomEngine(seed),
    )


def test_world_simulator_returns_visibility_on_background_event():
    events = simulate_world(_context(), [])

    assert events[0].visibility == "reader"


def test_world_simulator_uses_weighted_table_roll():
    events = simulate_world(_context(), [])

    assert events[0].effects["_roll"]["type"] == "table"
    assert events[0].effects["_roll"]["table"]["table"] == "background_events"


def test_world_simulator_is_deterministic_with_fixed_seed():
    assert simulate_world(_context("same"), []) == simulate_world(_context("same"), [])


def test_background_event_visibility_is_required():
    with pytest.raises(ValidationError):
        BackgroundEventCandidate.model_validate({"description": "missing visibility"})
