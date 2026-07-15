import pytest

from living_narrative.agents.conflict_resolver import resolve_conflicts
from living_narrative.agents.models import (
    CharacterAgentOutput,
    CharacterQuestUpdateCandidate,
    EmotionDeltaCandidate,
    GoalUpdateCandidate,
    InventoryUpdateCandidate,
    RelationshipUpdateCandidate,
)
from living_narrative.agents.state_manager import build_state_diff
from living_narrative.narration.models import NarratorQuestUpdateCandidate, ThreadUpdateCandidate
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import ActionCandidate
from living_narrative.random.engine import RandomEngine
from living_narrative.state.diff import apply_state_diff
from living_narrative.state.models import (
    AffordanceOutcome,
    CharacterState,
    Event,
    FactionState,
    GmVaultEntry,
    LLMConfig,
    ProjectConfig,
    Quest,
    ReaderStateEntry,
    RelationshipState,
    SceneAffordance,
    SceneState,
    SceneStatus,
    ThreatTrack,
    UnresolvedThread,
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


def _context(
    gm_vault=None,
    threats=None,
    scenes=None,
    characters=None,
    decay=0,
    relationships=None,
    unresolved_threads=None,
    factions=None,
    quests=None,
) -> TurnContext:
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
        world=WorldState(
            id="world_001",
            name="World",
            summary="",
            threats=threats or [],
            emotion_decay_per_turn=decay,
        ),
        characters=characters
        or [CharacterState(id="char_001", name="A", role="r", emotions={"fear": 30})],
        scenes=scenes
        if scenes is not None
        else [SceneState(id="scene_001", location="loc", time="now")],
        gm_vault=gm_vault or [],
        factions=factions or [],
        relationships=relationships or [],
        unresolved_threads=unresolved_threads or [],
        quests=quests or [],
    )
    return TurnContext(1, project, None, bundle, RandomEngine("seed"))


def _empty_character_output(*, quest_updates=None):
    return CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        quest_updates=quest_updates or [],
    )


def test_character_quest_advance_resolve_apply_only_to_existing_quest_through_diff():
    context = _context(quests=[Quest(id="quest_001", title="出口を探す", status="open")])
    output = _empty_character_output(
        quest_updates=[
            CharacterQuestUpdateCandidate(action="advance", quest_id="quest_001"),
            CharacterQuestUpdateCandidate(action="resolve", quest_id="quest_001"),
        ]
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert context.bundle.quests[0].status == "open"
    applied = apply_state_diff(context.bundle, result.diff).bundle
    assert applied.quests[0].status == "resolved"


def test_successful_combat_damage_is_an_hp_delta_with_existing_clamp():
    context = _context(
        characters=[CharacterState(id="char_002", name="B", role="r", stats={"hp": 3})]
    )
    event = Event(
        id="event_0001",
        turn=1,
        type="combat",
        text="攻撃が命中した",
        visibility="reader",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "脱出する",
                "result": "success",
                "damage": 5,
            }
        },
    )

    result = build_state_diff(context, [event], [])

    hp_change = next(change for change in result.diff.changes if change.path == "stats.hp")
    assert hp_change.target == "character"
    assert hp_change.id == "char_002"
    assert hp_change.op == "delta"
    assert hp_change.value == -5
    assert context.bundle.characters[0].stats["hp"] == 3
    applied = apply_state_diff(context.bundle, result.diff).bundle
    assert applied.characters[0].stats["hp"] == 0


def test_narrator_can_open_reader_visible_quest():
    update = NarratorQuestUpdateCandidate(
        action="open",
        quest_id="quest_001",
        title="出口を探す",
        objectives=["案内図を確認する"],
    )

    result = build_state_diff(_context(), [], [], narrator_quest_updates=[update])
    applied = apply_state_diff(_context().bundle, result.diff).bundle

    assert applied.quests[0].title == "出口を探す"
    assert applied.quests[0].objectives == ["案内図を確認する"]


def test_character_open_is_defensively_rejected_with_reason():
    update = CharacterQuestUpdateCandidate.model_construct(
        action="open",
        quest_id="quest_001",
        title="私だけが知る目標",
        objectives=["秘密を守る"],
    )
    output = _empty_character_output(quest_updates=[update])

    result = build_state_diff(_context(), [], [], character_outputs=[("char_001", output)])

    assert not result.diff.changes
    assert result.rejected_changes[0].reason == "character cannot open reader-visible quest"


def test_quest_related_event_ids_include_only_reader_events():
    events = [
        Event(id="event_0001", turn=1, type="x", text="reader", visibility="reader"),
        Event(id="event_0002", turn=1, type="x", text="canon", visibility="canon"),
        Event(id="event_0003", turn=1, type="x", text="scene", visibility="scene"),
        Event(id="event_0004", turn=1, type="x", text="character", visibility="character"),
        Event(id="event_0005", turn=1, type="x", text="gm", visibility="gm_only"),
    ]
    update = NarratorQuestUpdateCandidate(action="open", quest_id="quest_001", title="公開目標")

    result = build_state_diff(_context(), events, [], narrator_quest_updates=[update])
    applied = apply_state_diff(_context().bundle, result.diff).bundle

    assert applied.quests[0].related_event_ids == ["event_0001"]


@pytest.mark.parametrize("status", ["resolved", "failed"])
def test_quest_terminal_status_rejects_transition_with_reason(status):
    context = _context(quests=[Quest(id="quest_001", title="出口を探す", status=status)])
    update = NarratorQuestUpdateCandidate(action="advance", quest_id="quest_001")

    result = build_state_diff(context, [], [], narrator_quest_updates=[update])

    assert not result.diff.changes
    assert status in result.rejected_changes[0].reason


@pytest.mark.parametrize(
    ("update", "reason"),
    [
        (NarratorQuestUpdateCandidate(action="resolve", quest_id="quest_999"), "unknown"),
        (
            NarratorQuestUpdateCandidate(action="open", quest_id="quest_001", title="重複"),
            "duplicate",
        ),
        (
            NarratorQuestUpdateCandidate(action="open", quest_id="bad", title="不正"),
            "invalid",
        ),
    ],
)
def test_invalid_quest_updates_are_rejected_with_reason(update, reason):
    context = _context(quests=[Quest(id="quest_001", title="出口を探す", status="open")])

    result = build_state_diff(context, [], [], narrator_quest_updates=[update])

    assert not result.diff.changes
    assert reason in result.rejected_changes[0].reason


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


def test_emotion_delta_for_unknown_emotion_key_is_rejected():
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[EmotionDeltaCandidate(emotion="nostalgia", delta=10)],
        goal_updates=[],
    )

    result = build_state_diff(_context(), [], [], character_outputs=[("char_001", output)])

    assert [c for c in result.diff.changes if c.target == "character"] == []
    assert any(
        item.reason == "unknown emotion key for character" for item in result.rejected_changes
    )


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


def test_emotion_decay_pulls_down_toward_baseline_when_above_it():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 80},
        emotions_baseline={"fear": 30},
    )
    context = _context(characters=[character], decay=5)

    result = build_state_diff(context, [], [])

    emotion_changes = [c for c in result.diff.changes if c.target == "character"]
    assert len(emotion_changes) == 1
    change = emotion_changes[0]
    assert change.path == "emotions.fear"
    assert change.value == -5
    assert change.visibility == Visibility.CHARACTER


def test_emotion_decay_pulls_up_toward_baseline_when_below_it():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 10},
        emotions_baseline={"fear": 30},
    )
    context = _context(characters=[character], decay=5)

    result = build_state_diff(context, [], [])

    emotion_changes = [c for c in result.diff.changes if c.target == "character"]
    assert len(emotion_changes) == 1
    assert emotion_changes[0].value == 5


def test_emotion_decay_min_step_lands_exactly_on_baseline_without_overshoot():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 32},
        emotions_baseline={"fear": 30},
    )
    context = _context(characters=[character], decay=5)

    result = build_state_diff(context, [], [])
    applied = apply_state_diff(context.bundle, result.diff)

    emotion_changes = [c for c in result.diff.changes if c.target == "character"]
    assert emotion_changes[0].value == -2
    assert applied.bundle.characters[0].emotions["fear"] == 30


def test_emotion_decay_rate_zero_produces_no_changes():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 80},
        emotions_baseline={"fear": 30},
    )
    context = _context(characters=[character], decay=0)

    result = build_state_diff(context, [], [])

    assert [c for c in result.diff.changes if c.target == "character"] == []


def test_emotion_decay_skips_emotion_keys_missing_a_baseline():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 80, "curiosity": 60},
        emotions_baseline={"fear": 30},
    )
    context = _context(characters=[character], decay=5)

    result = build_state_diff(context, [], [])

    emotion_changes = [c for c in result.diff.changes if c.target == "character"]
    assert len(emotion_changes) == 1
    assert emotion_changes[0].path == "emotions.fear"


def test_emotion_decay_skips_dead_characters():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 80},
        emotions_baseline={"fear": 30},
        status="dead",
    )
    context = _context(characters=[character], decay=5)

    result = build_state_diff(context, [], [])

    assert [c for c in result.diff.changes if c.target == "character"] == []


def test_emotion_decay_and_character_output_delta_both_apply_cleanly_in_one_diff():
    character = CharacterState(
        id="char_001",
        name="A",
        role="r",
        emotions={"fear": 50},
        emotions_baseline={"fear": 30},
    )
    context = _context(characters=[character], decay=5)
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[EmotionDeltaCandidate(emotion="fear", delta=10)],
        goal_updates=[],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    emotion_changes = [c for c in result.diff.changes if c.target == "character"]
    assert len(emotion_changes) == 2

    applied = apply_state_diff(context.bundle, result.diff)
    # +10 from the character output, then -5 decay applied in diff order: 50 + 10 - 5 = 55
    assert applied.bundle.characters[0].emotions["fear"] == 55


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


def test_relationship_update_produces_a_relationship_delta_change_and_applies():
    relationship = RelationshipState(
        **{"from": "char_001", "to": "char_002"},
        trust=50,
        affection=50,
        tension=50,
        suspicion=50,
    )
    context = _context(
        characters=[
            CharacterState(id="char_001", name="A", role="r"),
            CharacterState(id="char_002", name="B", role="r"),
        ],
        relationships=[relationship],
    )
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        relationship_updates=[
            RelationshipUpdateCandidate(to="char_002", dimension="trust", delta=10)
        ],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    relationship_changes = [c for c in result.diff.changes if c.target == "relationship"]
    assert len(relationship_changes) == 1
    change = relationship_changes[0]
    assert change.id == "char_001__char_002"
    assert change.op == "delta"
    assert change.path == "trust"
    assert change.value == 10
    assert change.visibility == Visibility.CHARACTER

    applied = apply_state_diff(context.bundle, result.diff)
    assert applied.bundle.relationships[0].trust == 60


def test_relationship_update_clamps_to_100_on_apply():
    relationship = RelationshipState(
        **{"from": "char_001", "to": "char_002"},
        trust=95,
        affection=50,
        tension=50,
        suspicion=50,
    )
    context = _context(
        characters=[
            CharacterState(id="char_001", name="A", role="r"),
            CharacterState(id="char_002", name="B", role="r"),
        ],
        relationships=[relationship],
    )
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        relationship_updates=[
            RelationshipUpdateCandidate(to="char_002", dimension="trust", delta=15)
        ],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    applied = apply_state_diff(context.bundle, result.diff)

    assert applied.bundle.relationships[0].trust == 100


def test_relationship_update_targeting_self_is_rejected():
    context = _context(
        characters=[CharacterState(id="char_001", name="A", role="r")],
        relationships=[],
    )
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        relationship_updates=[
            RelationshipUpdateCandidate(to="char_001", dimension="trust", delta=10)
        ],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert [c for c in result.diff.changes if c.target == "relationship"] == []
    assert any(
        item.reason == "relationship update targets self" for item in result.rejected_changes
    )


def test_relationship_update_for_missing_pair_is_rejected():
    context = _context(
        characters=[
            CharacterState(id="char_001", name="A", role="r"),
            CharacterState(id="char_002", name="B", role="r"),
        ],
        relationships=[],
    )
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        relationship_updates=[
            RelationshipUpdateCandidate(to="char_002", dimension="trust", delta=10)
        ],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert [c for c in result.diff.changes if c.target == "relationship"] == []
    assert any(item.reason == "relationship pair not found" for item in result.rejected_changes)


def test_character_agent_output_default_empty_relationship_updates_is_back_compat():
    output = CharacterAgentOutput(action_candidates=[], emotion_deltas=[], goal_updates=[])

    result = build_state_diff(_context(), [], [], character_outputs=[("char_001", output)])

    assert [c for c in result.diff.changes if c.target == "relationship"] == []
    assert [c for c in result.diff.changes if c.path.startswith("inventory")] == []


def test_inventory_gain_allocates_after_max_item_number_and_applies_as_diff():
    character = CharacterState.model_validate(
        {
            "id": "char_001",
            "name": "A",
            "role": "r",
            "inventory": [{"id": "item_004", "name": "鍵", "qty": 1}],
        }
    )
    context = _context(characters=[character])
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        inventory_updates=[InventoryUpdateCandidate(action="gain", name="包帯", qty=2)],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert context.bundle.characters[0].inventory == character.inventory
    change = next(change for change in result.diff.changes if change.path == "inventory")
    assert change.op == "add"
    assert change.value.id == "item_005"
    applied = apply_state_diff(context.bundle, result.diff)
    assert applied.bundle.characters[0].inventory[-1].name == "包帯"
    assert applied.bundle.characters[0].inventory[-1].qty == 2


@pytest.mark.parametrize("action", ["use", "lose"])
def test_inventory_use_or_lose_reduces_qty_through_diff(action):
    character = CharacterState.model_validate(
        {
            "id": "char_001",
            "name": "A",
            "role": "r",
            "inventory": [{"id": "item_001", "name": "包帯", "qty": 3}],
        }
    )
    context = _context(characters=[character])
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        inventory_updates=[InventoryUpdateCandidate(action=action, item_id="item_001", qty=2)],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert context.bundle.characters[0].inventory[0].qty == 3
    change = next(change for change in result.diff.changes if "inventory" in change.path)
    assert (change.op, change.path, change.value) == ("set", "inventory.item_001.qty", 1)
    applied = apply_state_diff(context.bundle, result.diff)
    assert applied.bundle.characters[0].inventory[0].qty == 1


def test_inventory_use_of_all_stock_removes_item_through_diff():
    character = CharacterState.model_validate(
        {
            "id": "char_001",
            "name": "A",
            "role": "r",
            "inventory": [{"id": "item_001", "name": "包帯", "qty": 2}],
        }
    )
    context = _context(characters=[character])
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        inventory_updates=[InventoryUpdateCandidate(action="use", item_id="item_001", qty=2)],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])
    applied = apply_state_diff(context.bundle, result.diff)

    assert applied.bundle.characters[0].inventory == []


def test_inventory_updates_reject_cumulative_stock_overrun():
    character = CharacterState.model_validate(
        {
            "id": "char_001",
            "name": "A",
            "role": "r",
            "inventory": [{"id": "item_001", "name": "包帯", "qty": 2}],
        }
    )
    context = _context(characters=[character])
    output = CharacterAgentOutput(
        action_candidates=[],
        emotion_deltas=[],
        goal_updates=[],
        inventory_updates=[
            InventoryUpdateCandidate(action="use", item_id="item_001", qty=1),
            InventoryUpdateCandidate(action="lose", item_id="item_001", qty=2),
        ],
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert len([change for change in result.diff.changes if "inventory" in change.path]) == 1
    assert any("exceeds stock" in rejected.reason for rejected in result.rejected_changes)


@pytest.mark.parametrize(
    ("update", "reason"),
    [
        (InventoryUpdateCandidate(action="use", item_id="item_999"), "unknown inventory item"),
        (InventoryUpdateCandidate(action="lose", item_id="item_001", qty=3), "exceeds stock"),
        (InventoryUpdateCandidate(action="gain", name="鍵", qty=0), "qty must be positive"),
    ],
)
def test_invalid_inventory_updates_are_rejected_without_partial_mutation(update, reason):
    character = CharacterState.model_validate(
        {
            "id": "char_001",
            "name": "A",
            "role": "r",
            "inventory": [{"id": "item_001", "name": "包帯", "qty": 2}],
        }
    )
    context = _context(characters=[character])
    output = CharacterAgentOutput(
        action_candidates=[], emotion_deltas=[], goal_updates=[], inventory_updates=[update]
    )

    result = build_state_diff(context, [], [], character_outputs=[("char_001", output)])

    assert [change for change in result.diff.changes if "inventory" in change.path] == []
    assert any(reason in rejected.reason for rejected in result.rejected_changes)
    assert context.bundle.characters[0].inventory[0].qty == 2


def test_scene_summary_update_produces_a_scene_summary_set_diff():
    result = build_state_diff(_context(), [], [], scene_summary_update="霧の奥へ歩き始めた。")

    scene_changes = [c for c in result.diff.changes if c.target == "scene"]
    assert len(scene_changes) == 1
    change = scene_changes[0]
    assert change.id == "scene_001"
    assert change.op == "set"
    assert change.path == "summary"
    assert change.value == "霧の奥へ歩き始めた。"
    assert change.visibility == Visibility.SCENE

    applied = apply_state_diff(_context().bundle, result.diff)
    assert applied.bundle.scenes[0].summary == "霧の奥へ歩き始めた。"


def test_no_scene_summary_update_produces_no_scene_change():
    result = build_state_diff(_context(), [], [], scene_summary_update=None)

    assert [c for c in result.diff.changes if c.target == "scene"] == []


def test_blank_scene_summary_update_produces_no_scene_change():
    result = build_state_diff(_context(), [], [], scene_summary_update="")

    assert [c for c in result.diff.changes if c.target == "scene"] == []


def test_threat_pressure_event_generates_a_world_set_diff():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=10, pressure_per_turn="2d6")
    event = Event(
        id="event_0001",
        turn=1,
        type="threat_pressure",
        text="Pursuer draws closer",
        visibility=Visibility.GM_ONLY,
        effects={"threat_id": "threat_001", "pressure": 22},
    )

    output = build_state_diff(_context(threats=[threat]), [event], [])

    change = next(c for c in output.diff.changes if c.target == "world")
    assert change.op == "set"
    assert change.path == "threats.threat_001.pressure"
    assert change.value == 22
    assert change.visibility == Visibility.GM_ONLY
    assert change.source_event == "event_0001"


def test_threat_pressure_diff_applies_to_the_matching_threat_and_rolls_back():
    threat_a = ThreatTrack(id="threat_001", name="Pursuer", pressure=10, pressure_per_turn="2d6")
    threat_b = ThreatTrack(id="threat_002", name="Other", pressure=5, pressure_per_turn="1d6")
    context = _context(threats=[threat_a, threat_b])
    event = Event(
        id="event_0001",
        turn=1,
        type="threat_pressure",
        text="Pursuer draws closer",
        visibility=Visibility.GM_ONLY,
        effects={"threat_id": "threat_001", "pressure": 22},
    )

    output = build_state_diff(context, [event], [])
    applied = apply_state_diff(context.bundle, output.diff)

    assert applied.bundle.world.threats[0].pressure == 22
    assert applied.bundle.world.threats[1].pressure == 5

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    assert restored.world.threats[0].pressure == 10


def _faction() -> FactionState:
    return FactionState(
        id="faction_001",
        name="Mist Keepers",
        public_face="old station committee",
        resources={"influence": 45, "secrecy": 70},
        relations={"char_001": 40, "char_004": 15},
    )


def _faction_move_event(**effects) -> Event:
    return Event(
        id="event_0001",
        turn=1,
        type="faction_move",
        text="Mist Keepers move",
        visibility=Visibility.GM_ONLY,
        effects={
            "faction_id": "faction_001",
            "resource_deltas": {"influence": -5},
            "relation_deltas": {"char_004": 10},
            **effects,
        },
    )


def test_faction_move_event_generates_resource_and_relation_delta_diffs():
    output = build_state_diff(_context(factions=[_faction()]), [_faction_move_event()], [])

    faction_changes = [c for c in output.diff.changes if c.target == "faction"]
    assert [(c.path, c.value) for c in faction_changes] == [
        ("resources.influence", -5),
        ("relations.char_004", 10),
    ]
    assert all(c.id == "faction_001" for c in faction_changes)
    assert all(c.visibility == Visibility.GM_ONLY for c in faction_changes)
    assert all(c.source_event == "event_0001" for c in faction_changes)


def test_faction_move_diff_applies_and_rolls_back():
    context = _context(factions=[_faction()])

    output = build_state_diff(context, [_faction_move_event()], [])
    applied = apply_state_diff(context.bundle, output.diff)

    assert applied.bundle.factions[0].resources["influence"] == 40
    assert applied.bundle.factions[0].relations["char_004"] == 25

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    assert restored.factions[0].resources["influence"] == 45
    assert restored.factions[0].relations["char_004"] == 15


def test_faction_move_unknown_faction_is_rejected_with_reason():
    output = build_state_diff(
        _context(factions=[_faction()]),
        [_faction_move_event(faction_id="faction_999")],
        [],
    )

    assert [c for c in output.diff.changes if c.target == "faction"] == []
    assert output.rejected_changes[0].reason == "unknown faction_id: 'faction_999'"


def test_faction_move_unknown_resource_key_is_rejected_with_reason():
    output = build_state_diff(
        _context(factions=[_faction()]),
        [_faction_move_event(resource_deltas={"unknown": -5}, relation_deltas={})],
        [],
    )

    assert [c for c in output.diff.changes if c.target == "faction"] == []
    assert output.rejected_changes[0].reason == "unknown faction resource key: 'unknown'"


def test_faction_move_unknown_relation_key_is_rejected_with_reason():
    output = build_state_diff(
        _context(factions=[_faction()]),
        [_faction_move_event(resource_deltas={}, relation_deltas={"char_999": 5})],
        [],
    )

    assert [c for c in output.diff.changes if c.target == "faction"] == []
    assert output.rejected_changes[0].reason == "unknown faction relation key: 'char_999'"


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


def _transition_scenes(scene_002_active_characters=None):
    return [
        SceneState(
            id="scene_001",
            location="loc",
            time="now",
            active_characters=["char_001"],
            status=SceneStatus.ACTIVE,
        ),
        SceneState(
            id="scene_002",
            location="next loc",
            time="now",
            active_characters=scene_002_active_characters or [],
            status=SceneStatus.PENDING,
        ),
    ]


def _transition_event(**effects):
    return Event(
        id="event_0001",
        turn=1,
        type="threat_stage",
        text="追跡者が現れる",
        visibility=Visibility.READER,
        effects={"scene_transition": effects},
    )


def test_scene_transition_end_and_start_produce_three_diffs_and_apply_rollback_restores():
    context = _context(scenes=_transition_scenes())
    event = _transition_event(end="scene_001", start="scene_002")

    output = build_state_diff(context, [event], [])
    scene_changes = [c for c in output.diff.changes if c.target == "scene"]

    assert output.rejected_changes == []
    assert len(scene_changes) == 3
    assert {
        (c.id, c.path, c.value if not isinstance(c.value, list) else tuple(c.value))
        for c in scene_changes
    } == {
        ("scene_001", "status", "ended"),
        ("scene_002", "status", "active"),
        ("scene_002", "active_characters", ("char_001",)),
    }
    for change in scene_changes:
        assert change.source_event == "event_0001"
        assert change.visibility == Visibility.CANON

    applied = apply_state_diff(context.bundle, output.diff)
    scene_001 = next(s for s in applied.bundle.scenes if s.id == "scene_001")
    scene_002 = next(s for s in applied.bundle.scenes if s.id == "scene_002")
    assert scene_001.status == "ended"
    assert scene_002.status == "active"
    assert scene_002.active_characters == ["char_001"]

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    restored_001 = next(s for s in restored.scenes if s.id == "scene_001")
    restored_002 = next(s for s in restored.scenes if s.id == "scene_002")
    assert restored_001.status == "active"
    assert restored_002.status == "pending"
    assert restored_002.active_characters == []


def test_scene_transition_start_target_missing_is_rejected():
    context = _context(scenes=_transition_scenes())
    event = _transition_event(end="scene_001", start="scene_999")

    output = build_state_diff(context, [event], [])

    assert any(c.target == "scene" and c.id == "scene_999" for c in output.diff.changes) is False
    assert any(
        item.reason == "scene_transition start target not found" for item in output.rejected_changes
    )
    # end side still succeeds independently
    assert any(
        c.target == "scene" and c.id == "scene_001" and c.value == "ended"
        for c in output.diff.changes
    )


def test_scene_transition_start_target_not_pending_is_rejected():
    scenes = _transition_scenes()
    scenes[1].status = SceneStatus.ACTIVE
    context = _context(scenes=scenes)
    event = _transition_event(end="scene_001", start="scene_002")

    output = build_state_diff(context, [event], [])

    assert any(
        item.reason == "scene_transition start target not pending"
        for item in output.rejected_changes
    )
    assert not any(c.target == "scene" and c.id == "scene_002" for c in output.diff.changes)


def test_scene_transition_start_only_activates_without_carry_over_when_no_end():
    context = _context(scenes=_transition_scenes())
    event = _transition_event(start="scene_002")

    output = build_state_diff(context, [event], [])
    scene_changes = [c for c in output.diff.changes if c.target == "scene"]

    assert output.rejected_changes == []
    assert len(scene_changes) == 1
    assert scene_changes[0].id == "scene_002"
    assert scene_changes[0].path == "status"
    assert scene_changes[0].value == "active"


def test_scene_transition_end_only_just_ends_the_scene():
    context = _context(scenes=_transition_scenes())
    event = _transition_event(end="scene_001")

    output = build_state_diff(context, [event], [])
    scene_changes = [c for c in output.diff.changes if c.target == "scene"]

    assert output.rejected_changes == []
    assert len(scene_changes) == 1
    assert scene_changes[0].id == "scene_001"
    assert scene_changes[0].path == "status"
    assert scene_changes[0].value == "ended"


def test_scene_transition_does_not_overwrite_predefined_active_characters():
    context = _context(scenes=_transition_scenes(scene_002_active_characters=["char_001"]))
    event = _transition_event(end="scene_001", start="scene_002")

    output = build_state_diff(context, [event], [])
    scene_changes = [c for c in output.diff.changes if c.target == "scene"]

    assert output.rejected_changes == []
    assert len(scene_changes) == 2
    assert not any(c.path == "active_characters" for c in scene_changes)

    applied = apply_state_diff(context.bundle, output.diff)
    scene_002 = next(s for s in applied.bundle.scenes if s.id == "scene_002")
    assert scene_002.active_characters == ["char_001"]


def test_active_scene_id_skips_pending_scenes_for_scene_summary_update():
    scenes = _transition_scenes()  # scene_001 active, scene_002 pending
    context = _context(scenes=scenes)

    result = build_state_diff(context, [], [], scene_summary_update="次の場面へ。")

    scene_changes = [c for c in result.diff.changes if c.target == "scene"]
    assert len(scene_changes) == 1
    assert scene_changes[0].id == "scene_001"


def test_active_scene_id_is_none_when_only_pending_scenes_exist():
    scenes = [
        SceneState(
            id="scene_002",
            location="loc",
            time="now",
            status=SceneStatus.PENDING,
        )
    ]
    context = _context(scenes=scenes)

    result = build_state_diff(context, [], [], scene_summary_update="次の場面へ。")

    assert [c for c in result.diff.changes if c.target == "scene"] == []


# --- Issue 014: thread_updates -----------------------------------------------------------


def test_open_thread_update_adds_a_new_thread_and_applies():
    context = _context()
    candidate = ThreadUpdateCandidate(action="open", description="お守りの由来は謎のままだ。")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    thread_changes = [c for c in result.diff.changes if c.target == "threads"]
    assert len(thread_changes) == 1
    change = thread_changes[0]
    assert change.op == "add"
    assert change.path == ""
    assert change.value["id"] == "thread_000101"
    assert change.value["description"] == "お守りの由来は謎のままだ。"
    assert change.value["status"] == "open"
    assert change.value["opened_turn"] == 1
    assert result.rejected_changes == []

    applied = apply_state_diff(context.bundle, result.diff)
    assert len(applied.bundle.unresolved_threads) == 1
    assert applied.bundle.unresolved_threads[0].id == "thread_000101"

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    assert restored.unresolved_threads == []


def test_open_thread_update_without_description_is_rejected():
    context = _context()
    candidate = ThreadUpdateCandidate(action="open")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert [c for c in result.diff.changes if c.target == "threads"] == []
    assert any(
        item.reason == "open thread update missing description" for item in result.rejected_changes
    )


def test_advance_thread_update_appends_note_and_links_this_turns_events_and_applies():
    thread = UnresolvedThread(id="thread_000101", description="お守りの由来", status="open")
    context = _context(unresolved_threads=[thread])
    event = Event(
        id="event_0001",
        turn=1,
        type="character_action",
        text="お守りを拾った",
        visibility=Visibility.READER,
    )
    candidate = ThreadUpdateCandidate(
        action="advance", thread_id="thread_000101", note="お守りを見つけた。"
    )

    result = build_state_diff(context, [event], [], _ids(), thread_updates=[candidate])

    thread_changes = [c for c in result.diff.changes if c.target == "threads"]
    note_changes = [c for c in thread_changes if c.path == "notes"]
    event_link_changes = [c for c in thread_changes if c.path == "related_event_ids"]
    assert len(note_changes) == 1
    assert note_changes[0].value == "お守りを見つけた。"
    assert len(event_link_changes) == 1
    assert event_link_changes[0].value == "event_0001"
    assert result.rejected_changes == []

    applied = apply_state_diff(context.bundle, result.diff)
    updated = applied.bundle.unresolved_threads[0]
    assert updated.notes == ["お守りを見つけた。"]
    assert updated.related_event_ids == ["event_0001"]
    assert updated.status == "open"

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    assert restored.unresolved_threads[0].notes == []
    assert restored.unresolved_threads[0].related_event_ids == []


def test_advance_thread_update_without_note_only_links_events():
    thread = UnresolvedThread(id="thread_000101", description="お守りの由来", status="open")
    context = _context(unresolved_threads=[thread])
    candidate = ThreadUpdateCandidate(action="advance", thread_id="thread_000101")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert [c for c in result.diff.changes if c.target == "threads" and c.path == "notes"] == []
    assert result.rejected_changes == []


def test_resolve_thread_update_sets_status_and_applies():
    thread = UnresolvedThread(id="thread_000101", description="お守りの由来", status="open")
    context = _context(unresolved_threads=[thread])
    candidate = ThreadUpdateCandidate(action="resolve", thread_id="thread_000101")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    thread_changes = [c for c in result.diff.changes if c.target == "threads"]
    assert len(thread_changes) == 1
    assert thread_changes[0].op == "set"
    assert thread_changes[0].path == "status"
    assert thread_changes[0].value == "resolved"
    assert result.rejected_changes == []

    applied = apply_state_diff(context.bundle, result.diff)
    assert applied.bundle.unresolved_threads[0].status == "resolved"

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    assert restored.unresolved_threads[0].status == "open"


def test_advance_unknown_thread_id_is_rejected():
    context = _context()
    candidate = ThreadUpdateCandidate(action="advance", thread_id="thread_999999", note="x")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert [c for c in result.diff.changes if c.target == "threads"] == []
    assert any("unknown thread_id" in item.reason for item in result.rejected_changes)


def test_resolve_unknown_thread_id_is_rejected():
    context = _context()
    candidate = ThreadUpdateCandidate(action="resolve", thread_id="thread_999999")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert [c for c in result.diff.changes if c.target == "threads"] == []
    assert any("unknown thread_id" in item.reason for item in result.rejected_changes)


def test_advance_on_already_resolved_thread_is_rejected():
    thread = UnresolvedThread(id="thread_000101", description="お守りの由来", status="resolved")
    context = _context(unresolved_threads=[thread])
    candidate = ThreadUpdateCandidate(action="advance", thread_id="thread_000101", note="x")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert [c for c in result.diff.changes if c.target == "threads"] == []
    assert any("already resolved" in item.reason for item in result.rejected_changes)


def test_resolve_on_already_resolved_thread_is_rejected():
    thread = UnresolvedThread(id="thread_000101", description="お守りの由来", status="resolved")
    context = _context(unresolved_threads=[thread])
    candidate = ThreadUpdateCandidate(action="resolve", thread_id="thread_000101")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert [c for c in result.diff.changes if c.target == "threads"] == []
    assert any("already resolved" in item.reason for item in result.rejected_changes)


def test_thread_update_actions_emit_synthetic_thread_update_events_in_timeline():
    thread = UnresolvedThread(id="thread_000501", description="お守りの由来", status="open")
    context = _context(unresolved_threads=[thread])
    candidates = [
        ThreadUpdateCandidate(action="open", description="新しい謎"),
        ThreadUpdateCandidate(action="advance", thread_id="thread_000501", note="進展した"),
    ]

    result = build_state_diff(context, [], [], _ids(), thread_updates=candidates)

    thread_events = [e for e in result.synthetic_events if e.type == "thread_update"]
    assert len(thread_events) == 2
    assert {e.effects["action"] for e in thread_events} == {"open", "advance"}
    for event in thread_events:
        assert event.visibility == Visibility.GM_ONLY
        assert event.cause == "narrator"

    timeline_change = next(c for c in result.diff.changes if c.target == "timeline")
    for event in thread_events:
        assert event.id in timeline_change.value["event_ids"]


def test_rejected_thread_updates_emit_no_synthetic_event():
    context = _context()
    candidate = ThreadUpdateCandidate(action="advance", thread_id="thread_999999", note="x")

    result = build_state_diff(context, [], [], _ids(), thread_updates=[candidate])

    assert result.synthetic_events == []


def test_no_thread_updates_produces_no_threads_changes():
    result = build_state_diff(_context(), [], [], thread_updates=None)

    assert [c for c in result.diff.changes if c.target == "threads"] == []


def test_multiple_open_thread_updates_get_distinct_ids():
    candidates = [
        ThreadUpdateCandidate(action="open", description="謎その1"),
        ThreadUpdateCandidate(action="open", description="謎その2"),
    ]

    result = build_state_diff(_context(), [], [], _ids(), thread_updates=candidates)

    thread_changes = [c for c in result.diff.changes if c.target == "threads"]
    assert [c.value["id"] for c in thread_changes] == ["thread_000101", "thread_000102"]


def _authored_action_event(context, outcome, *, affordance_id="affordance_001"):
    context.bundle.scenes[0].active_characters = ["char_001"]
    context.bundle.scenes[0].affordances = [
        SceneAffordance(
            id=affordance_id,
            text="作者定義の行動",
            visibility=Visibility.READER,
            outcomes=outcome if isinstance(outcome, list) else [outcome],
        )
    ]
    allocator = _ids()
    events = resolve_conflicts(
        context,
        [],
        [
            ActionCandidate(
                character_id="char_001",
                action_text="行動する",
                intent={"affordance_id": affordance_id},
            )
        ],
        allocator,
        lambda roll: None,
    )
    return events, allocator


def test_authored_thread_open_sets_runtime_turn_provenance_and_wins_over_narrator():
    context = _context()
    outcome = AffordanceOutcome(
        target="threads",
        op="add",
        value={
            "id": "thread_000101",
            "description": "公開された謎",
            "status": "open",
            "related_event_ids": [],
            "notes": [],
        },
        visibility=Visibility.READER,
    )
    events, allocator = _authored_action_event(context, outcome)

    result = build_state_diff(
        context,
        events,
        [],
        allocator,
        thread_updates=[ThreadUpdateCandidate(action="open", description="Narrator duplicate")],
    )

    change = next(c for c in result.diff.changes if c.target == "threads" and c.op == "add")
    assert change.value["opened_turn"] == context.turn
    assert change.source_event == events[-1].id
    authored_event = next(e for e in result.synthetic_events if e.type == "thread_update")
    assert authored_event.cause == "authored:affordance_001"
    assert authored_event.visibility == Visibility.READER
    assert any("conflicts with authored thread" in item.reason for item in result.rejected_changes)
    applied = apply_state_diff(context.bundle, result.diff).bundle
    assert applied.unresolved_threads[0].description == "公開された謎"
    assert applied.unresolved_threads[0].opened_turn == context.turn


def test_authored_thread_resolve_wins_over_narrator_conflict():
    thread = UnresolvedThread(
        id="thread_000101", description="公開された謎", status="open", opened_turn=2
    )
    context = _context(unresolved_threads=[thread])
    outcome = AffordanceOutcome(
        target="threads",
        op="set",
        path="status",
        id="thread_000101",
        value="resolved",
        visibility=Visibility.READER,
    )
    events, allocator = _authored_action_event(context, outcome)

    result = build_state_diff(
        context,
        events,
        [],
        allocator,
        thread_updates=[ThreadUpdateCandidate(action="resolve", thread_id="thread_000101")],
    )

    status_change = next(
        c for c in result.diff.changes if c.target == "threads" and c.path == "status"
    )
    assert status_change.value == "resolved"
    assert status_change.source_event == events[-1].id
    authored_event = next(e for e in result.synthetic_events if e.type == "thread_update")
    assert authored_event.effects == {
        "action": "resolve",
        "thread_id": "thread_000101",
        "authored": True,
    }
    assert any("conflicts with authored thread" in item.reason for item in result.rejected_changes)
    assert apply_state_diff(context.bundle, result.diff).bundle.unresolved_threads[0].status == (
        "resolved"
    )


def test_authored_thread_cannot_advance_after_resolve_in_same_outcome():
    thread = UnresolvedThread(
        id="thread_000101", description="公開された謎", status="open", opened_turn=2
    )
    context = _context(unresolved_threads=[thread])
    outcomes = [
        AffordanceOutcome(
            target="threads",
            op="set",
            path="status",
            id=thread.id,
            value=value,
            visibility=Visibility.READER,
        )
        for value in ("resolved", "advanced")
    ]
    events, allocator = _authored_action_event(context, outcomes)

    result = build_state_diff(context, events, [], allocator)

    status_changes = [
        change
        for change in result.diff.changes
        if change.target == "threads" and change.path == "status"
    ]
    assert [change.value for change in status_changes] == ["resolved"]
    assert any(item.reason == "resolved_thread_is_terminal" for item in result.rejected_changes)


def test_authored_thread_cannot_reopen_resolved_state():
    thread = UnresolvedThread(
        id="thread_000101", description="回収済み", status="resolved", opened_turn=2
    )
    context = _context(unresolved_threads=[thread])
    outcome = AffordanceOutcome(
        target="threads",
        op="set",
        path="status",
        id=thread.id,
        value="advanced",
        visibility=Visibility.READER,
    )
    events, allocator = _authored_action_event(context, outcome)

    result = build_state_diff(context, events, [], allocator)

    assert [change for change in result.diff.changes if change.target == "threads"] == []
    assert any(item.reason == "resolved_thread_is_terminal" for item in result.rejected_changes)


def test_reader_invisible_authored_thread_outcome_is_rejected():
    outcome = AffordanceOutcome.model_construct(
        target="threads",
        op="add",
        value={
            "id": "thread_000101",
            "description": "GM secret thread",
            "status": "open",
        },
        visibility=Visibility.GM_ONLY,
    )

    with pytest.raises(ValueError, match="reader-safe visibility"):
        SceneAffordance(
            id="affordance_001",
            text="secret",
            visibility=Visibility.GM_ONLY,
            outcomes=[outcome],
        )


# --- Issue 015: memory_summary_update -----------------------------------------------------


def test_memory_summary_update_adds_a_memory_change_and_applies():
    context = _context()
    context.turn = 10

    result = build_state_diff(
        context, [], [], _ids(), memory_summary_update="これまでの物語の要約その1。"
    )

    memory_changes = [c for c in result.diff.changes if c.target == "memory"]
    assert len(memory_changes) == 1
    change = memory_changes[0]
    assert change.op == "add"
    assert change.path == ""
    assert change.value["id"] == "memory_0010"
    assert change.value["up_to_turn"] == 10
    assert change.value["text"] == "これまでの物語の要約その1。"
    assert change.visibility == Visibility.READER
    assert result.rejected_changes == []

    applied = apply_state_diff(context.bundle, result.diff)
    assert len(applied.bundle.memory_summaries) == 1
    assert applied.bundle.memory_summaries[0].text == "これまでの物語の要約その1。"

    restored = apply_state_diff(applied.bundle, applied.inverse_diff).bundle
    assert restored.memory_summaries == []


def test_blank_memory_summary_update_is_a_no_op():
    result = build_state_diff(_context(), [], [], _ids(), memory_summary_update="")

    assert [c for c in result.diff.changes if c.target == "memory"] == []


def test_none_memory_summary_update_is_a_no_op():
    result = build_state_diff(_context(), [], [], _ids(), memory_summary_update=None)

    assert [c for c in result.diff.changes if c.target == "memory"] == []
