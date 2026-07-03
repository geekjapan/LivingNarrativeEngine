from living_narrative.agents.conflict_resolver import resolve_conflicts
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import ActionCandidate, WorldEventCandidate
from living_narrative.random.engine import RandomEngine
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
