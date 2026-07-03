from living_narrative.agents.state_manager import build_state_diff
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import (
    CharacterState,
    Event,
    LLMConfig,
    ProjectConfig,
    SceneState,
    Visibility,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)


def _context() -> TurnContext:
    project = ProjectConfig(
        id="p",
        title="P",
        genre="g",
        tone="t",
        autonomy_level="auto",
        user_mode="watcher",
        random_seed="seed",
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock"),
        workspace=WorkspaceConfig(root=".", state="state", runs="runs", exports="exports"),
    )
    bundle = WorldStateBundle(
        world=WorldState(id="world_001", name="World", summary=""),
        characters=[CharacterState(id="char_001", name="A", role="r")],
        scenes=[SceneState(id="scene_001", location="loc", time="now")],
    )
    return TurnContext(1, project, None, bundle, RandomEngine("seed"))


def test_resolved_death_event_generates_status_dead_diff():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_death",
        text="A dies",
        visibility=Visibility.CANON,
        effects={"character_id": "char_001"},
    )

    output = build_state_diff(_context(), [event], [])

    assert output.diff.changes[0].path == "status"
    assert output.diff.changes[0].value == "dead"
    assert output.diff.changes[0].source_event == "event_0001"


def test_scene_end_event_generates_status_ended_diff():
    event = Event(
        id="event_0001",
        turn=1,
        type="scene_end",
        text="Scene ends",
        visibility=Visibility.CANON,
        effects={"scene_id": "scene_001"},
    )

    output = build_state_diff(_context(), [event], [])

    assert output.diff.changes[0].target == "scene"
    assert output.diff.changes[0].value == "ended"


def test_must_not_reveal_reader_state_change_is_rejected():
    event = Event(
        id="event_0001",
        turn=1,
        type="reveal",
        text="Reveal",
        visibility=Visibility.READER,
        effects={"reveal_text": "secret"},
    )

    output = build_state_diff(
        _context(),
        [event],
        [{"type": "reveal_control", "mode": "must-not-reveal", "target_id": "secret"}],
    )

    assert output.diff.changes == []
    assert "must-not-reveal" in output.rejected_changes[0].reason


def test_missing_target_change_is_rejected():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_death",
        text="Unknown dies",
        visibility=Visibility.CANON,
        effects={"character_id": "char_999"},
    )

    output = build_state_diff(_context(), [event], [])

    assert output.diff.changes == []
    assert "not found" in output.rejected_changes[0].reason
