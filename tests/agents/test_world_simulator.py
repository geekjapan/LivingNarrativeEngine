import pytest
from pydantic import ValidationError

from living_narrative.agents.models import BackgroundEventCandidate
from living_narrative.agents.world_simulator import simulate_world
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import (
    BackgroundEventTableEntry,
    LLMConfig,
    ProjectConfig,
    ThreatStage,
    ThreatTrack,
    Visibility,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)


def _context(
    seed: str = "seed",
    background_events: list[BackgroundEventTableEntry] | None = None,
    threats: list[ThreatTrack] | None = None,
    turn: int = 1,
) -> TurnContext:
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
        turn=turn,
        project=project,
        paths=None,
        bundle=WorldStateBundle(
            world=WorldState(
                id="world_001",
                name="World",
                summary="",
                background_events=background_events or [],
                threats=threats or [],
            )
        ),
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


def test_background_event_uses_world_state_table_when_populated():
    table = [
        BackgroundEventTableEntry(text="霧が濃くなる", weight=5),
        BackgroundEventTableEntry(text="遠くで足音がする", weight=1),
    ]

    events = simulate_world(_context(background_events=table), [])

    background_event = next(e for e in events if e.type == "background_event")
    assert background_event.text in {entry.text for entry in table}
    assert background_event.effects["_roll"]["table"]["table"] == "background_events"


def test_background_event_falls_back_to_hardcoded_entries_when_table_empty():
    events = simulate_world(_context(background_events=[]), [])

    background_event = next(e for e in events if e.type == "background_event")
    assert background_event.text in {"静かな時間が流れる", "遠くで不穏な物音がする"}


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


# Issue 008: threat escalation tracks.


def _pressure_roll(seed: str = "seed", turn: int = 1) -> int:
    """The pressure roll a fresh 2d6 threat produces for a given seed/turn (0 starting pressure
    makes the resulting ``pressure`` effect equal to the raw roll)."""
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")
    events = simulate_world(_context(seed, threats=[threat], turn=turn), [])
    return next(e for e in events if e.type == "threat_pressure").effects["pressure"]


def test_no_threats_produces_no_threat_events():
    events = simulate_world(_context(), [])

    assert all(e.type not in {"threat_pressure", "threat_stage"} for e in events)


def test_threat_with_no_stages_emits_only_a_pressure_event():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")

    events = simulate_world(_context(threats=[threat]), [])

    assert [e.type for e in events if e.type.startswith("threat_")] == ["threat_pressure"]


def test_threat_pressure_event_is_gm_only_and_carries_the_roll():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=10, pressure_per_turn="2d6")

    events = simulate_world(_context(threats=[threat]), [])

    event = next(e for e in events if e.type == "threat_pressure")
    assert event.visibility == "gm_only"
    assert event.effects["threat_id"] == "threat_001"
    assert event.effects["_roll"]["type"] == "dice"
    assert event.effects["_roll"]["dice"]["notation"] == "2d6"
    assert event.effects["roll_id"] == event.effects["_roll"]["id"]
    assert event.effects["pressure"] == 10 + event.effects["_roll"]["result"]


def test_threat_pressure_clamps_to_100():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=99, pressure_per_turn="2d6")

    events = simulate_world(_context(threats=[threat]), [])

    event = next(e for e in events if e.type == "threat_pressure")
    assert event.effects["pressure"] == 100


def test_threat_stage_not_yet_crossed_does_not_fire():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=roll + 1, text="not yet", visibility=Visibility.SCENE)],
    )

    events = simulate_world(_context(threats=[threat]), [])

    assert [e for e in events if e.type == "threat_stage"] == []


def test_threat_stage_crossed_by_the_roll_fires_once():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=roll, text="足音が近づく", visibility=Visibility.SCENE)],
    )

    events = simulate_world(_context(threats=[threat]), [])

    stage_events = [e for e in events if e.type == "threat_stage"]
    assert len(stage_events) == 1
    assert stage_events[0].text == "足音が近づく"
    assert stage_events[0].visibility == "scene"
    assert stage_events[0].effects["threat_id"] == "threat_001"
    assert stage_events[0].effects["stage_at"] == roll
    assert (
        stage_events[0].effects["roll_id"]
        == next(e for e in events if e.type == "threat_pressure").effects["roll_id"]
    )


def test_threat_stage_carries_arbitrary_effects_like_scene_transition():
    """Issue 009: scene_transition is just another key in ThreatStage.effects (data-driven,
    no world_simulator code path dedicated to it)."""
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[
            ThreatStage(
                at=roll,
                text="追跡者が姿を現す",
                visibility=Visibility.READER,
                effects={"scene_transition": {"end": "scene_001", "start": "scene_002"}},
            )
        ],
    )

    events = simulate_world(_context(threats=[threat]), [])

    stage_event = next(e for e in events if e.type == "threat_stage")
    assert stage_event.effects["scene_transition"] == {"end": "scene_001", "start": "scene_002"}


def test_multiple_thresholds_crossed_in_one_roll_all_fire_in_ascending_order():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[
            ThreatStage(at=roll, text="second", visibility=Visibility.READER),
            ThreatStage(at=1, text="first", visibility=Visibility.SCENE),
        ],
    )

    events = simulate_world(_context(threats=[threat]), [])

    stage_events = [e for e in events if e.type == "threat_stage"]
    assert [e.text for e in stage_events] == ["first", "second"]


def test_already_past_stage_never_refires():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=roll,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=roll, text="already happened", visibility=Visibility.SCENE)],
    )

    events = simulate_world(_context(threats=[threat]), [])

    assert [e for e in events if e.type == "threat_stage"] == []


def test_threat_events_are_deterministic_with_fixed_seed():
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=5, text="closer", visibility=Visibility.SCENE)],
    )

    first = simulate_world(_context("same-seed", threats=[threat]), [])
    second = simulate_world(_context("same-seed", threats=[threat]), [])

    assert first == second
