import pytest

from living_narrative.agents.conflict_resolver import resolve_conflicts
from living_narrative.agents.state_manager import build_state_diff
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import ActionCandidate, WorldEventCandidate
from living_narrative.random.engine import RandomEngine
from living_narrative.session.stop_conditions import StopConditionName, evaluate_stop_conditions
from living_narrative.state.diff import StateDiff, apply_state_diff
from living_narrative.state.models import (
    AffordanceOutcome,
    AffordancePrerequisites,
    CharacterState,
    LLMConfig,
    PacingConfig,
    ProjectConfig,
    SceneAffordance,
    SceneState,
    Visibility,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)
from living_narrative.workspace.loader import WorkspacePaths


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
        characters=[
            CharacterState(id="char_001", name="A", role="r"),
            CharacterState(id="char_002", name="B", role="r"),
        ],
        scenes=[
            SceneState(
                id="scene_001",
                location="loc",
                time="now",
                active_characters=["char_002", "char_001"],
            )
        ],
    )
    return TurnContext(1, project, None, bundle, RandomEngine("seed"))


def _ids():
    index = 0

    def allocate():
        nonlocal index
        index += 1
        return f"event_{index:04d}"

    return allocate


def test_same_target_actions_are_resolved_with_roll():
    rolls = []
    actions = [
        ActionCandidate(character_id="char_001", action_text="A", target_id="door"),
        ActionCandidate(character_id="char_002", action_text="B", target_id="door"),
    ]

    events = resolve_conflicts(_context(), [], actions, _ids(), rolls.append)

    assert len(events) == 1
    assert len(rolls) == 1
    assert events[0].roll_ids == [rolls[0].id]


def test_conflict_rng_consumption_is_candidate_count_minus_one():
    rolls = []
    actions = [
        ActionCandidate(character_id="char_001", action_text="A", target_id="door"),
        ActionCandidate(character_id="char_002", action_text="B", target_id="door"),
    ]
    world = [
        WorldEventCandidate(
            type="background",
            text="C",
            visibility=Visibility.READER,
            target_id="door",
        )
    ]

    resolve_conflicts(_context(), world, actions, _ids(), rolls.append)

    assert len([roll for roll in rolls if roll.type == "chance"]) == 2


def test_life_or_death_conflict_marks_roll_critical():
    rolls = []
    actions = [
        ActionCandidate(
            character_id="char_001",
            action_text="kill attempt",
            target_id="char_002",
            effects={"life_or_death": True},
        ),
        ActionCandidate(character_id="char_002", action_text="dodge", target_id="char_002"),
    ]

    resolve_conflicts(_context(), [], actions, _ids(), rolls.append)

    assert rolls[0].severity == "critical"


def test_resolved_event_tracks_source_candidate():
    actions = [ActionCandidate(character_id="char_001", action_text="A", source_index=3)]

    events = resolve_conflicts(_context(), [], actions, _ids(), lambda roll: None)

    assert events[0].cause == "character:char_001:3"


def test_combat_uses_stats_and_skills_for_one_linked_roll():
    context = _context()
    context.bundle.characters[0].stats = {"strength": 12, "hp": 20}
    context.bundle.characters[0].skills = {"sword": 8}
    context.bundle.characters[1].stats = {"hp": 15}
    rolls = []
    combat = ActionCandidate(
        character_id="char_001",
        action_text="剣で斬りかかる",
        target_id="char_002",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "退路を確保する",
                "stat": "strength",
                "skill": "sword",
                "target": 50,
                "damage": 4,
            }
        },
    )

    events = resolve_conflicts(context, [], [combat], _ids(), rolls.append)

    assert len(rolls) == 1
    assert rolls[0].chance.modifiers == {"stat:strength": 12, "skill:sword": 8}
    assert events[0].type == "combat"
    assert events[0].roll_ids == [rolls[0].id]
    assert events[0].effects["combat"] == {
        "attacker": "char_001",
        "defender": "char_002",
        "stakes": "退路を確保する",
        "result": rolls[0].outcome,
        "damage": 4 if rolls[0].outcome == "success" else 0,
        "life_or_death": False,
    }


def test_successful_combat_prevents_stall_fallback_double_fire():
    context = _context()
    context.turn = 4
    context.bundle.world.pacing = PacingConfig(stall_window=3)
    context.bundle.scenes[0].affordances = [
        SceneAffordance(
            id="affordance_001",
            text="fallback",
            visibility="scene",
            fallback_only=True,
            outcomes=[
                AffordanceOutcome(
                    target="scene",
                    op="set",
                    path="status",
                    id="scene_001",
                    value="ended",
                    visibility="reader",
                )
            ],
        )
    ]
    context.bundle.scenes[0].fallback_affordance_ids = ["affordance_001"]
    context.bundle.characters[0].stats = {"hp": 20, "strength": 10}
    context.bundle.characters[1].stats = {"hp": 20}
    combat = ActionCandidate(
        character_id="char_001",
        action_text="strike",
        target_id="char_002",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "advance",
                "stat": "strength",
                "target": 100,
                "damage": 1,
            }
        },
    )

    events = resolve_conflicts(context, [], [combat], _ids(), lambda roll: None)

    assert [event.type for event in events] == ["combat"]


def _stall_context(tmp_path, *, pacing_terminal=False, fallback=None):
    context = _context()
    context.paths = WorkspacePaths(
        root=tmp_path,
        state=tmp_path / "state",
        runs=tmp_path / "runs",
        exports=tmp_path / "exports",
    )
    context.turn = 4
    context.bundle.world.pacing = PacingConfig(stall_window=3)
    context.bundle.scenes[0].pacing_terminal = pacing_terminal
    context.bundle.scenes[0].affordances = list(fallback or [])
    context.bundle.scenes[0].fallback_affordance_ids = [item.id for item in fallback or []]
    return context


def _advancing_affordance(
    affordance_id: str,
    *,
    fallback_only=False,
    used_event_ids=None,
    recurrence="once",
    exclusive=False,
):
    return SceneAffordance(
        id=affordance_id,
        text="作者定義の進展",
        visibility=Visibility.READER,
        recurrence=recurrence,
        fallback_only=fallback_only,
        used_event_ids=used_event_ids or [],
        exclusive=exclusive,
        outcomes=[
            AffordanceOutcome(
                target="scene",
                op="set",
                path="status",
                id="scene_001",
                value="ended",
                visibility=Visibility.READER,
            )
        ],
    )


def test_accepted_action_outcome_prevents_stall_fallback_double_fire(tmp_path):
    normal = _advancing_affordance("affordance_001")
    fallback = _advancing_affordance("affordance_002", fallback_only=True)
    context = _stall_context(tmp_path, fallback=[normal, fallback])
    action = ActionCandidate(
        character_id="char_001",
        action_text="扉を開ける",
        intent={"affordance_id": normal.id},
    )

    events = resolve_conflicts(context, [], [action], _ids(), lambda roll: None)

    assert [event.type for event in events] == ["character_action", "action_outcome"]
    assert events[-1].effects["accepted"] is True


def test_no_effect_intent_is_rejected_and_does_not_suppress_fallback(tmp_path):
    no_effect = _advancing_affordance("affordance_001")
    no_effect.outcomes[0].value = "active"
    fallback = _advancing_affordance("affordance_002", fallback_only=True)
    context = _stall_context(tmp_path, fallback=[no_effect, fallback])
    action = ActionCandidate(
        character_id="char_001",
        action_text="already active",
        intent={"affordance_id": no_effect.id},
    )

    events = resolve_conflicts(context, [], [action], _ids(), lambda roll: None)

    assert [event.type for event in events] == [
        "character_action",
        "action_intent_rejected",
        "character_action",
        "action_outcome",
    ]
    assert events[1].effects["reason"] == "no_effect"
    assert events[-1].effects["action_outcome"]["affordance_id"] == fallback.id


def test_structured_intent_success_emits_seeded_roll_exact_outcome_and_diff():
    context = _context()
    affordance = _advancing_affordance("affordance_001")
    affordance.success_chance = 50
    context.bundle.scenes[0].affordances = [affordance]
    rolls = []
    allocator = _ids()
    events = resolve_conflicts(
        context,
        [],
        [
            ActionCandidate(
                character_id="char_001",
                action_text="扉を開ける",
                effects={"stats": {"hp": -99}},
                intent={"affordance_id": affordance.id},
            )
        ],
        allocator,
        rolls.append,
    )

    assert [event.type for event in events] == ["character_action", "action_outcome"]
    assert len(rolls) == 1
    outcome_event = events[-1]
    assert outcome_event.roll_ids == [rolls[0].id]
    assert outcome_event.effects["action_outcome"] == {
        "affordance_id": "affordance_001",
        "character_id": "char_001",
        "outcomes": [
            {
                "target": "scene",
                "op": "set",
                "path": "status",
                "id": "scene_001",
                "value": "ended",
                "visibility": "reader",
            }
        ],
        "consumption": {"recurrence": "once", "exclusive": False, "fallback": False},
    }

    result = build_state_diff(context, events, [], allocator)
    scene_status = next(
        change
        for change in result.diff.changes
        if change.target == "scene" and change.path == "status"
    )
    used_change = next(
        change
        for change in result.diff.changes
        if change.path == "affordances.affordance_001.used_event_ids"
    )
    assert scene_status.value == "ended"
    assert used_change.value == outcome_event.id
    assert apply_state_diff(context.bundle, result.diff).bundle.scenes[0].status == "ended"


def test_free_text_action_effects_cannot_mutate_state():
    context = _context()
    action = ActionCandidate(
        character_id="char_001",
        action_text="自由文だけでHPを減らす",
        effects={"stats": {"hp": -99}, "scene_status": "ended"},
    )

    events = resolve_conflicts(context, [], [action], _ids(), lambda roll: None)
    diff = build_state_diff(context, events, []).diff

    assert "stats" not in events[0].effects
    assert [change for change in diff.changes if change.target != "timeline"] == []


def test_stalled_turn_uses_fallback_only_when_no_normal_outcome(tmp_path):
    fallback = _advancing_affordance("affordance_001", fallback_only=True)
    context = _stall_context(tmp_path, fallback=[fallback])

    events = resolve_conflicts(context, [], [], _ids(), lambda roll: None)

    assert [event.type for event in events] == ["character_action", "action_outcome"]
    assert events[-1].effects["action_outcome"]["consumption"]["fallback"] is True


@pytest.mark.parametrize(
    "fallback",
    [
        _advancing_affordance("affordance_001", fallback_only=True, used_event_ids=["event_0000"]),
        None,
    ],
)
def test_stalled_turn_without_eligible_fallback_emits_pacing_exhausted(tmp_path, fallback):
    context = _stall_context(tmp_path, fallback=[fallback] if fallback is not None else [])

    events = resolve_conflicts(context, [], [], _ids(), lambda roll: None)

    assert [event.type for event in events] == ["pacing_exhausted"]
    assert events[0].visibility == Visibility.GM_ONLY


def test_pacing_terminal_suppresses_exhausted_error(tmp_path):
    context = _stall_context(tmp_path, pacing_terminal=True)

    assert resolve_conflicts(context, [], [], _ids(), lambda roll: None) == []


def test_unknown_hidden_and_prerequisite_failed_intents_are_sanitized(tmp_path):
    context = _context()
    context.paths = WorkspacePaths(
        root=tmp_path,
        state=tmp_path / "state",
        runs=tmp_path / "runs",
        exports=tmp_path / "exports",
    )
    context.bundle.scenes[0].affordances = [
        SceneAffordance(
            id="affordance_998",
            text="hidden-value",
            visibility=Visibility.GM_ONLY,
            outcomes=[
                AffordanceOutcome(
                    target="scene",
                    op="set",
                    path="status",
                    id="scene_001",
                    value="ended",
                    visibility=Visibility.GM_ONLY,
                )
            ],
        ),
        SceneAffordance(
            id="affordance_997",
            text="locked",
            visibility=Visibility.READER,
            prerequisites=AffordancePrerequisites(required_fact_ids=["fact_missing"]),
            outcomes=[
                AffordanceOutcome(
                    target="scene",
                    op="set",
                    path="status",
                    id="scene_001",
                    value="ended",
                    visibility=Visibility.READER,
                )
            ],
        ),
    ]
    actions = [
        ActionCandidate(character_id="char_001", action_text="try", intent={"affordance_id": id_})
        for id_ in ("affordance_999", "affordance_998", "affordance_997")
    ]

    events = resolve_conflicts(context, [], actions, _ids(), lambda roll: None)
    rejected = [event for event in events if event.type == "action_intent_rejected"]

    assert len(rejected) == 3
    assert all(event.visibility == Visibility.GM_ONLY for event in rejected)
    public_artifact = " ".join(
        event.model_dump_json() for event in events if event.visibility != Visibility.GM_ONLY
    )
    assert "affordance_998" not in public_artifact
    assert "hidden-value" not in public_artifact
    assert {event.effects["reason"] for event in rejected} == {
        "unknown_affordance",
        "not_visible",
        "prerequisites_unmet",
    }


@pytest.mark.parametrize(
    ("recurrence", "exclusive"),
    [("once", False), ("unlimited", True)],
)
def test_same_turn_exclusive_or_once_intent_is_rejected_after_first_acceptance(
    recurrence, exclusive
):
    affordance = _advancing_affordance("affordance_001", recurrence=recurrence, exclusive=exclusive)
    context = _context()
    context.bundle.scenes[0].affordances = [affordance]
    actions = [
        ActionCandidate(
            character_id="char_001",
            action_text="同じ行動",
            intent={"affordance_id": affordance.id},
        ),
        ActionCandidate(
            character_id="char_001",
            action_text="同じ行動を再試行",
            intent={"affordance_id": affordance.id},
        ),
    ]

    events = resolve_conflicts(context, [], actions, _ids(), lambda roll: None)

    assert [event.type for event in events] == [
        "character_action",
        "action_outcome",
        "character_action",
        "action_intent_rejected",
    ]
    assert events[-1].effects["reason"] == "already_triggered"


def test_same_seed_reproduces_action_events_rolls_and_diff():
    def run_once():
        context = _context()
        affordance = _advancing_affordance("affordance_001")
        affordance.success_chance = 50
        context.bundle.scenes[0].affordances = [affordance]
        rolls = []
        events = resolve_conflicts(
            context,
            [],
            [
                ActionCandidate(
                    character_id="char_001",
                    action_text="扉を開ける",
                    intent={"affordance_id": affordance.id},
                )
            ],
            _ids(),
            rolls.append,
        )
        from living_narrative.agents.state_manager import build_state_diff

        diff = build_state_diff(context, events, []).diff
        return (
            [event.model_dump(mode="json") for event in events],
            [roll.model_dump(mode="json") for roll in rolls],
            diff.model_dump(mode="json"),
        )

    assert run_once() == run_once()


def test_combat_is_contested_before_the_winning_candidate_is_resolved():
    context = _context()
    context.bundle.characters[0].stats = {"hp": 20}
    context.bundle.characters[1].stats = {"strength": 12, "hp": 15}
    combat = ActionCandidate(
        character_id="char_002",
        action_text="突破口を開く",
        target_id="char_001",
        effects={
            "exclusive": True,
            "combat": {
                "attacker": "char_002",
                "defender": "char_001",
                "stakes": "門を突破する",
                "stat": "strength",
                "target": 0,
                "damage": 4,
                "life_or_death": True,
            },
        },
    )
    blocker = ActionCandidate(
        character_id="char_001",
        action_text="門を封鎖する",
        target_id="char_001",
        effects={"exclusive": True},
    )
    rolls = []

    events = resolve_conflicts(context, [], [blocker, combat], _ids(), rolls.append)

    assert len(events) == 1
    assert events[0].type == "combat"
    assert [roll.label for roll in rolls] == [
        "conflict_resolver.contested",
        "combat:char_002:char_001",
    ]
    assert [roll.severity for roll in rolls] == ["normal", "critical"]
    assert events[0].roll_ids == [roll.id for roll in rolls]
    stops = evaluate_stop_conditions(
        project=context.project,
        autonomy_level="assist",
        diff=StateDiff(id="diff_0001", turn=1),
        checks=[],
        rolls=rolls,
    )
    assert [stop.name for stop in stops] == [StopConditionName.HEAVY_ROLL_FAILURE]


def test_losing_life_or_death_combat_selection_roll_is_normal_and_does_not_stop():
    context = _context()
    context.random_engine = RandomEngine("combat-win")
    context.bundle.characters[0].stats = {"hp": 20}
    context.bundle.characters[1].stats = {"strength": 12, "hp": 15}
    combat = ActionCandidate(
        character_id="char_002",
        action_text="決死の突破を試みる",
        target_id="char_001",
        effects={
            "exclusive": True,
            "combat": {
                "attacker": "char_002",
                "defender": "char_001",
                "stakes": "命を賭けて突破する",
                "stat": "strength",
                "target": 0,
                "damage": 4,
                "life_or_death": True,
            },
        },
    )
    blocker = ActionCandidate(
        character_id="char_001",
        action_text="突破を阻止する",
        target_id="char_001",
        effects={"exclusive": True},
    )
    rolls = []

    events = resolve_conflicts(context, [], [blocker, combat], _ids(), rolls.append)

    assert events[0].type == "character_action"
    assert len(rolls) == 1
    assert rolls[0].outcome == "failure"
    assert rolls[0].severity == "normal"
    assert (
        evaluate_stop_conditions(
            project=context.project,
            autonomy_level="assist",
            diff=StateDiff(id="diff_0001", turn=1),
            checks=[],
            rolls=rolls,
        )
        == []
    )


def test_two_combat_candidates_contest_before_one_engagement_resolves():
    context = _context()
    context.bundle.characters[0].stats = {"strength": 8, "hp": 20}
    context.bundle.characters[1].stats = {"strength": 12, "hp": 15}
    context.bundle.characters.append(
        CharacterState(id="char_003", name="C", role="r", stats={"hp": 18})
    )
    context.bundle.scenes[0].active_characters.append("char_003")

    def combat(attacker):
        return ActionCandidate(
            character_id=attacker,
            action_text="敵へ攻撃する",
            target_id="char_003",
            effects={
                "combat": {
                    "attacker": attacker,
                    "defender": "char_003",
                    "stakes": "敵を退ける",
                    "stat": "strength",
                    "target": 100,
                    "damage": 3,
                }
            },
        )

    rolls = []
    events = resolve_conflicts(
        context, [], [combat("char_001"), combat("char_002")], _ids(), rolls.append
    )

    assert len(events) == 1
    assert events[0].effects["combat"]["attacker"] == "char_002"
    assert [roll.label for roll in rolls] == [
        "conflict_resolver.contested",
        "combat:char_002:char_003",
    ]


def test_world_combat_preserves_pre_roll_id_before_combat_roll():
    context = _context()
    context.bundle.characters[0].stats = {"strength": 12, "hp": 20}
    context.bundle.characters[1].stats = {"hp": 15}
    pre_roll = context.random_engine.roll_dice("1d6", turn=1, label="setup")
    candidate = WorldEventCandidate(
        type="ambush",
        text="待ち伏せが襲う",
        visibility=Visibility.READER,
        target_id="char_002",
        effects={
            "roll_id": pre_roll.id,
            "_roll": pre_roll.model_dump(mode="json"),
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "待ち伏せを退ける",
                "stat": "strength",
                "target": 50,
                "damage": 4,
            },
        },
    )
    rolls = []

    events = resolve_conflicts(context, [candidate], [], _ids(), rolls.append)

    assert len(rolls) == 2
    assert events[0].roll_ids == [pre_roll.id, rolls[1].id]


@pytest.mark.parametrize(
    ("combat", "message"),
    [
        (
            {
                "attacker": "char_999",
                "defender": "char_002",
                "stakes": "x",
                "stat": "hp",
                "target": 50,
                "damage": 1,
            },
            "character not found",
        ),
        (
            {
                "attacker": "char_001",
                "defender": "char_001",
                "stakes": "x",
                "stat": "hp",
                "target": 50,
                "damage": 1,
            },
            "must differ",
        ),
        (
            {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "x",
                "stat": "missing",
                "target": 50,
                "damage": 1,
            },
            "stat not found",
        ),
        (
            {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "x",
                "stat": "hp",
                "target": 50,
                "damage": 0,
            },
            "greater than 0",
        ),
        (
            {
                "attacker": 1,
                "defender": "char_002",
                "stakes": "x",
                "stat": "hp",
                "target": 50,
                "damage": 1,
            },
            "valid string",
        ),
        (
            {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "x",
                "stat": "hp",
                "target": "50",
                "damage": 1,
            },
            "valid integer",
        ),
        (
            {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "x",
                "stat": "hp",
                "target": 50,
                "damage": 1,
                "life_or_death": "true",
            },
            "valid boolean",
        ),
    ],
)
def test_combat_rejects_invalid_payloads(combat, message):
    context = _context()
    context.bundle.characters[0].stats = {"hp": 10}
    context.bundle.characters[1].stats = {"hp": 10}
    action = ActionCandidate(
        character_id="char_001",
        action_text="攻撃する",
        effects={"combat": combat},
    )

    rolls = []

    events = resolve_conflicts(context, [], [action], _ids(), rolls.append)

    assert rolls == []
    assert events[0].type == "combat_rejected"
    assert message in events[0].effects["reason"]
    assert events[0].visibility == Visibility.GM_ONLY


def test_invalid_combat_does_not_block_a_valid_candidate_or_consume_rng():
    context = _context()
    context.bundle.characters[0].stats = {"strength": 12, "hp": 20}
    context.bundle.characters[1].stats = {"hp": 15}
    invalid = ActionCandidate(
        character_id="char_001",
        action_text="不正な攻撃",
        target_id="char_999",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_999",
                "stakes": "不正",
                "stat": "strength",
                "target": 50,
                "damage": 4,
            }
        },
    )
    valid = ActionCandidate(
        character_id="char_001",
        action_text="有効な攻撃",
        target_id="char_002",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "退路を作る",
                "stat": "strength",
                "target": 50,
                "damage": 4,
            }
        },
    )
    rolls = []

    events = resolve_conflicts(context, [], [invalid, valid], _ids(), rolls.append)

    assert [event.type for event in events] == ["combat_rejected", "combat"]
    assert len(rolls) == 1
    assert rolls[0].label == "combat:char_001:char_002"


def test_combat_rejects_defender_outside_active_scene_without_consuming_rng():
    context = _context()
    context.bundle.characters[0].stats = {"strength": 12, "hp": 20}
    context.bundle.characters[1].stats = {"hp": 15}
    context.bundle.scenes[0].active_characters = ["char_001"]
    action = ActionCandidate(
        character_id="char_001",
        action_text="場面外の相手を攻撃する",
        target_id="char_002",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "不正な遠隔攻撃",
                "stat": "strength",
                "target": 50,
                "damage": 4,
            }
        },
    )
    rolls = []

    events = resolve_conflicts(context, [], [action], _ids(), rolls.append)

    assert rolls == []
    assert events[0].type == "combat_rejected"
    assert events[0].effects["reason"] == (
        "invalid combat: combat defender is outside active scene: char_002"
    )


def test_combat_uses_attackers_scene_when_multiple_scenes_are_active():
    context = _context()
    context.bundle.characters[0].stats = {"strength": 12, "hp": 20}
    context.bundle.characters[1].stats = {"hp": 15}
    context.bundle.scenes[0].active_characters = []
    context.bundle.scenes.append(
        SceneState(
            id="scene_002",
            location="別室",
            time="夜",
            status="active",
            active_characters=["char_001", "char_002"],
        )
    )
    action = ActionCandidate(
        character_id="char_001",
        action_text="同じ場面の相手を攻撃する",
        target_id="char_002",
        effects={
            "combat": {
                "attacker": "char_001",
                "defender": "char_002",
                "stakes": "別室を守る",
                "stat": "strength",
                "target": 100,
                "damage": 4,
            }
        },
    )
    rolls = []

    events = resolve_conflicts(context, [], [action], _ids(), rolls.append)

    assert events[0].type == "combat"
    assert len(rolls) == 1
