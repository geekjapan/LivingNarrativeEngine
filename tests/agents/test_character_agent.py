import pytest

from living_narrative.agents.character import PROMPT_TEXT, run_character_agent
from living_narrative.agents.models import CharacterAgentOutput
from living_narrative.llm.errors import StructuredOutputError
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.llm_gateway import LLMGateway
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


def _context(characters=None) -> TurnContext:
    characters = characters or [CharacterState(id="char_001", name="Aoi", role="detective")]
    project = ProjectConfig(
        id="p",
        title="P",
        genre="g",
        tone="t",
        autonomy_level="auto",
        user_mode="watcher",
        random_seed="seed",
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock-default"),
        workspace=WorkspaceConfig(root=".", state="state", runs="runs", exports="exports"),
        llm_profiles={"large": LLMConfig(provider="mock", model="mock-large")},
        llm_bindings={"character:char_001": "large"},
    )
    bundle = WorldStateBundle(
        world=WorldState(id="world_001", name="World", summary="Summary"),
        characters=characters,
        scenes=[
            SceneState(
                id="scene_001",
                location="駅",
                time="夜",
                active_characters=[c.id for c in characters],
            )
        ],
    )
    return TurnContext(
        turn=1,
        project=project,
        paths=None,
        bundle=bundle,
        random_engine=RandomEngine("seed"),
    )


def test_character_agent_uses_character_binding_key():
    context = _context()
    gateway = LLMGateway(project=context.project, random_seed="seed")

    run_character_agent(context, [], gateway)

    assert gateway.calls[0].binding_key == "character:char_001"
    assert gateway.calls[0].model == "mock-large"


def test_character_agent_prompt_mentions_scope_and_language_rules():
    assert "private_mind" in PROMPT_TEXT
    assert "GM vault" in PROMPT_TEXT
    assert "日本語" in PROMPT_TEXT
    assert '"character"' in PROMPT_TEXT


def test_character_agent_prompt_only_requests_inventory_updates_for_real_changes():
    assert "inventory_updates" in PROMPT_TEXT
    assert "実際に増減したときだけ" in PROMPT_TEXT


def test_character_agent_prompt_defines_minimal_combat_producer_contract():
    assert "effects.combat" in PROMPT_TEXT
    for field in ("attacker", "defender", "stakes", "target", "damage"):
        assert field in PROMPT_TEXT
    assert "scoped_state.id" in PROMPT_TEXT
    assert "eligible_combat_targets が空" in PROMPT_TEXT


def test_character_agent_is_deterministic_with_same_seed():
    first_context = _context()
    second_context = _context()

    first, _ = run_character_agent(
        first_context, [], LLMGateway(project=first_context.project, random_seed="seed")
    )
    second, _ = run_character_agent(
        second_context, [], LLMGateway(project=second_context.project, random_seed="seed")
    )

    assert first == second


def test_character_agent_schema_error_propagates():
    class BadGateway:
        calls = []

        def complete(self, binding_key, messages, response_schema, prompt_template_name):
            raise StructuredOutputError(
                provider_name="mock",
                model="mock",
                schema_name=CharacterAgentOutput.__name__,
                last_error="bad",
            )

    with pytest.raises(StructuredOutputError):
        run_character_agent(_context(), [], BadGateway())


def test_character_agent_includes_past_events_visible_to_character():
    context = _context()
    gateway = LLMGateway(project=context.project, random_seed="seed")
    past_events = [
        Event(
            id="event_0001",
            turn=1,
            type="narrative",
            text="past visible event",
            visibility=Visibility.READER,
        )
    ]

    _, records = run_character_agent(context, [], gateway, past_events=past_events)

    visible_texts = records[0].input_context["visible_events"]
    assert any(event["text"] == "past visible event" for event in visible_texts)


def test_character_agent_excludes_past_events_hidden_from_character():
    context = _context()
    gateway = LLMGateway(project=context.project, random_seed="seed")
    past_events = [
        Event(
            id="event_0001",
            turn=1,
            type="narrative",
            text="secret from Aoi",
            visibility=Visibility.SCENE,
            hidden_from=["char_001"],
        )
    ]

    _, records = run_character_agent(context, [], gateway, past_events=past_events)

    visible_texts = [event["text"] for event in records[0].input_context["visible_events"]]
    assert "secret from Aoi" not in visible_texts


def test_character_agent_defaults_past_events_to_none_backward_compatible():
    context = _context()
    gateway = LLMGateway(project=context.project, random_seed="seed")

    actions, records = run_character_agent(context, [], gateway)

    assert records[0].input_context["visible_events"] == []
    assert isinstance(actions, list)


def test_character_directive_reaches_only_its_target_characters_context():
    context = _context(
        characters=[
            CharacterState(id="char_001", name="Aoi", role="detective"),
            CharacterState(id="char_002", name="Ren", role="suspect"),
        ]
    )
    gateway = LLMGateway(project=context.project, random_seed="seed")
    intervention = {
        "id": "int_0001",
        "type": "character_directive",
        "target": {"kind": "character", "id": "char_001"},
        "content": "怪しい男に気づく",
    }

    _, records = run_character_agent(context, [], gateway, [intervention])

    by_character = {record.character_id: record.input_context["directives"] for record in records}
    assert by_character["char_001"] == [intervention]
    assert by_character["char_002"] == []
