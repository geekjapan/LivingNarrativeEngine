import pytest

from living_narrative.agents.conflict_resolver import resolve_conflicts
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import ActionCandidate, WorldEventCandidate
from living_narrative.random.engine import RandomEngine
from living_narrative.session.stop_conditions import StopConditionName, evaluate_stop_conditions
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import (
    CharacterState,
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
