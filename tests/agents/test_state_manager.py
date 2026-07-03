from living_narrative.agents.state_manager import build_state_diff
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import (
    CharacterState,
    Event,
    GmVaultEntry,
    LLMConfig,
    ProjectConfig,
    ReaderStateEntry,
    SceneState,
    Visibility,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)


def _ids():
    counter = 0

    def allocate():
        nonlocal counter
        counter += 1
        return f"event_{counter:04d}"

    return allocate


def _context(gm_vault=None) -> TurnContext:
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
        gm_vault=gm_vault or [],
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


def test_canon_edit_generates_a_synthetic_event_and_a_canon_state_diff():
    intervention = {
        "id": "int_0001",
        "turn": 1,
        "user_role": "full_gm",
        "type": "canon_edit",
        "target": {"kind": "canon"},
        "content": "新しい真実",
        "visibility": "canon",
    }

    output = build_state_diff(_context(), [], [intervention], _ids())

    assert len(output.synthetic_events) == 1
    synthetic = output.synthetic_events[0]
    assert synthetic.cause == "intervention:int_0001"
    assert output.diff.changes[0].target == "canon"
    assert output.diff.changes[0].op == "add"
    assert output.diff.changes[0].source_event == synthetic.id
    assert output.diff.changes[0].value["text"] == "新しい真実"


def test_hidden_truth_edit_generates_a_gm_vault_state_diff():
    intervention = {
        "id": "int_0002",
        "turn": 1,
        "user_role": "god",
        "type": "hidden_truth_edit",
        "target": {"kind": "gm_vault"},
        "content": "隠された真実",
        "visibility": "gm_only",
    }

    output = build_state_diff(_context(), [], [intervention], _ids())

    assert output.diff.changes[0].target == "gm_vault"
    assert output.diff.changes[0].value["text"] == "隠された真実"
    assert output.diff.changes[0].visibility == Visibility.GM_ONLY


def test_reveal_now_promotes_a_gm_vault_fact_to_reader_state():
    intervention = {
        "id": "int_0003",
        "turn": 1,
        "user_role": "full_gm",
        "type": "reveal_control",
        "target": {"kind": "gm_vault", "id": "gm_vault_001"},
        "content": "reveal it",
        "constraints": {"mode": "reveal-now"},
        "visibility": "reader",
    }
    context = _context(gm_vault=[GmVaultEntry(id="gm_vault_001", text="隠された真実")])

    output = build_state_diff(context, [], [intervention], _ids())

    assert len(output.synthetic_events) == 1
    synthetic = output.synthetic_events[0]
    assert synthetic.cause == "intervention:int_0003"
    change = output.diff.changes[0]
    assert change.target == "reader_state"
    assert change.value["text"] == "隠された真実"
    assert change.source_event == synthetic.id


def test_reveal_now_is_skipped_when_already_disclosed():
    intervention = {
        "id": "int_0004",
        "turn": 1,
        "user_role": "full_gm",
        "type": "reveal_control",
        "target": {"kind": "gm_vault", "id": "gm_vault_001"},
        "content": "reveal it",
        "constraints": {"mode": "reveal-now"},
        "visibility": "reader",
    }
    context = _context(gm_vault=[GmVaultEntry(id="gm_vault_001", text="既知の事実")])
    context.bundle.reader_state.append(
        ReaderStateEntry(
            id="reader_state_0001", text="既知の事実", established_turn=1, disclosed_turn=1
        )
    )

    output = build_state_diff(context, [], [intervention], _ids())

    assert output.diff.changes == []
    assert output.synthetic_events == []
