from living_narrative.agents.models import (
    CharacterAgentOutput,
    EmotionDeltaCandidate,
    GoalUpdateCandidate,
)
from living_narrative.agents.state_manager import build_state_diff
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.diff import apply_state_diff
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

    assert [c for c in output.diff.changes if c.target != "timeline"] == []
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

    assert [c for c in output.diff.changes if c.target != "timeline"] == []
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


def test_no_events_generates_no_timeline_change():
    output = build_state_diff(_context(), [], [])

    assert output.diff.changes == []


def test_resolved_event_generates_a_timeline_append_change():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_death",
        text="A dies",
        visibility=Visibility.CANON,
        effects={"character_id": "char_001"},
    )

    output = build_state_diff(_context(), [event], [])

    timeline_changes = [c for c in output.diff.changes if c.target == "timeline"]
    assert len(timeline_changes) == 1
    change = timeline_changes[0]
    assert change.op == "add"
    assert change.value["turn"] == 1
    assert change.value["event_ids"] == ["event_0001"]
    assert change.visibility == Visibility.CANON


def test_synthetic_event_is_included_in_the_timeline_append_change():
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

    timeline_changes = [c for c in output.diff.changes if c.target == "timeline"]
    assert len(timeline_changes) == 1
    assert timeline_changes[0].value["event_ids"] == [output.synthetic_events[0].id]


def test_emotion_delta_produces_a_character_delta_change_with_character_visibility():
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[EmotionDeltaCandidate(emotion="fear", delta=20)],
        goal_updates=[],
    )

    result = build_state_diff(_context(), [], [], character_outputs=[("char_001", output)])

    emotion_changes = [c for c in result.diff.changes if c.target == "character"]
    assert len(emotion_changes) == 1
    change = emotion_changes[0]
    assert change.id == "char_001"
    assert change.op == "delta"
    assert change.path == "emotions.fear"
    assert change.value == 20
    assert change.visibility == Visibility.CHARACTER


def test_emotion_delta_clamps_to_100_on_apply():
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[EmotionDeltaCandidate(emotion="fear", delta=30)],
        goal_updates=[],
    )
    context = _context()
    context.bundle.characters[0].emotions["fear"] = 90

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    applied = apply_state_diff(context.bundle, result.diff)

    assert applied.bundle.characters[0].emotions["fear"] == 100


def test_emotion_delta_clamps_to_0_on_apply():
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[EmotionDeltaCandidate(emotion="fear", delta=-90)],
        goal_updates=[],
    )
    context = _context()
    context.bundle.characters[0].emotions["fear"] = 10

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    applied = apply_state_diff(context.bundle, result.diff)

    assert applied.bundle.characters[0].emotions["fear"] == 0


def test_goal_update_appends_to_short_term_goals_on_apply():
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[GoalUpdateCandidate(goal_kind="short_term", content="find the caller")],
    )
    context = _context()

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    goal_changes = [c for c in result.diff.changes if c.target == "character"]
    assert goal_changes[0].op == "add"
    assert goal_changes[0].path == "goals.short_term"
    assert goal_changes[0].visibility == Visibility.CHARACTER

    applied = apply_state_diff(context.bundle, result.diff)
    assert applied.bundle.characters[0].goals.short_term == ["find the caller"]


def test_goal_update_appends_to_long_term_goals_on_apply():
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[GoalUpdateCandidate(goal_kind="long_term", content="escape the station")],
    )
    context = _context()

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    applied = apply_state_diff(context.bundle, result.diff)

    assert applied.bundle.characters[0].goals.long_term == ["escape the station"]
