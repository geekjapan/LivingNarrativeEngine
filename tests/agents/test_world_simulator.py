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


def test_world_directive_becomes_a_world_event_candidate():
    intervention = {
        "id": "int_0001",
        "type": "world_directive",
        "target": {"kind": "world"},
        "content": "雨が降り始める",
        "visibility": "reader",
    }

    events = simulate_world(_context(), [intervention])

    directive_event = next(e for e in events if e.type == "world_directive")
    assert directive_event.cause == "intervention:int_0001"
    assert directive_event.text == "雨が降り始める"
    assert directive_event.visibility == "reader"


def test_event_injection_becomes_a_world_event_candidate():
    intervention = {
        "id": "int_0002",
        "type": "event_injection",
        "target": {"kind": "world"},
        "content": "見知らぬ男が現れる",
        "visibility": "reader",
    }

    events = simulate_world(_context(), [intervention])

    assert any(e.type == "event_injection" and e.cause == "intervention:int_0002" for e in events)


def test_dice_roll_request_performs_a_roll_and_carries_it_for_recording():
    intervention = {
        "id": "int_0003",
        "type": "dice_roll_request",
        "target": {"kind": "roll"},
        "content": "気づくかどうか",
        "constraints": {"notation": "2d6", "target": 7},
        "visibility": "gm_only",
    }

    events = simulate_world(_context(), [intervention])

    roll_event = next(e for e in events if e.type == "dice_roll_request")
    assert roll_event.cause == "intervention:int_0003"
    assert roll_event.effects["_roll"]["dice"]["notation"] == "2d6"


def test_unrelated_intervention_types_do_not_produce_world_events():
    intervention = {
        "id": "int_0004",
        "type": "character_directive",
        "target": {"kind": "character"},
    }

    events = simulate_world(_context(), [intervention])

    assert all(e.type != "character_directive" for e in events)
