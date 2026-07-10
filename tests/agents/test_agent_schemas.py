import pytest
from pydantic import ValidationError

from living_narrative.agents.models import (
    ActionCandidate,
    CharacterAgentOutput,
    CharacterQuestUpdateCandidate,
    ConflictResolverOutput,
    InventoryUpdateCandidate,
    RelationshipUpdateCandidate,
    StateManagerOutput,
    WorldSimulatorOutput,
)
from living_narrative.pipeline.models import BuildDiffOutput
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import Event, Visibility


def test_character_agent_output_round_trips():
    output = CharacterAgentOutput(
        action_candidates=[
            ActionCandidate(kind="action", content="進む", visibility=Visibility.READER)
        ],
        emotion_deltas=[],
        goal_updates=[],
    )

    assert CharacterAgentOutput.model_validate_json(output.model_dump_json()) == output


def test_character_agent_output_defaults_relationship_updates_to_empty_list():
    output = CharacterAgentOutput(
        action_candidates=[
            ActionCandidate(kind="action", content="進む", visibility=Visibility.READER)
        ],
        emotion_deltas=[],
        goal_updates=[],
    )

    assert output.relationship_updates == []
    assert output.inventory_updates == []
    assert output.quest_updates == []


def test_inventory_update_candidate_round_trips():
    candidate = InventoryUpdateCandidate(action="gain", name="古い鍵", qty=2)

    assert InventoryUpdateCandidate.model_validate_json(candidate.model_dump_json()) == candidate


def test_character_quest_update_type_allows_only_advance_and_resolve():
    assert CharacterQuestUpdateCandidate(action="advance", quest_id="quest_001").action == "advance"
    with pytest.raises(ValidationError):
        CharacterQuestUpdateCandidate.model_validate(
            {
                "action": "open",
                "quest_id": "quest_001",
                "title": "私的目標",
                "objectives": ["秘密を守る"],
            }
        )
    with pytest.raises(ValidationError):
        CharacterQuestUpdateCandidate.model_validate(
            {"action": "advance", "quest_id": "quest_001", "title": "漏洩候補"}
        )


@pytest.mark.parametrize(
    "data",
    [
        {"action": "gain"},
        {"action": "use"},
        {"action": "lose"},
    ],
)
def test_inventory_update_candidate_requires_action_specific_fields(data):
    with pytest.raises(ValidationError):
        InventoryUpdateCandidate.model_validate(data)


def test_relationship_update_candidate_round_trips():
    candidate = RelationshipUpdateCandidate(to="char_002", dimension="trust", delta=10)

    assert RelationshipUpdateCandidate.model_validate_json(candidate.model_dump_json()) == candidate


def test_inner_reaction_visibility_is_clamped_to_character():
    candidate = ActionCandidate(
        kind="inner_reaction", content="まさか…", visibility=Visibility.READER
    )

    assert candidate.visibility == Visibility.CHARACTER


def test_inner_reaction_defaults_to_character_and_keeps_gm_only():
    assert ActionCandidate(kind="inner_reaction", content="内心").visibility == Visibility.CHARACTER
    assert (
        ActionCandidate(
            kind="inner_reaction", content="内心", visibility=Visibility.GM_ONLY
        ).visibility
        == Visibility.GM_ONLY
    )


def test_action_visibility_defaults_to_reader():
    assert ActionCandidate(kind="action", content="進む").visibility == Visibility.READER
    spoken = ActionCandidate(kind="dialogue", content="「行くぞ」", visibility=Visibility.SCENE)
    assert spoken.visibility == Visibility.SCENE


def test_world_simulator_output_requires_candidate_visibility():
    output = WorldSimulatorOutput.model_validate(
        {
            "time_advance": "one_turn",
            "parameter_drifts": [{"parameter": "danger_level", "delta": 1, "visibility": "canon"}],
            "faction_moves": [],
            "background_events": [
                {"description": "物音", "roll_id": "roll_0001", "visibility": "reader"}
            ],
        }
    )

    assert output.background_events[0].visibility == Visibility.READER


def test_conflict_resolver_output_round_trips_event_schema():
    output = ConflictResolverOutput(
        resolved_events=[
            Event(
                id="event_0001",
                turn=1,
                type="background_event",
                text="物音",
                visibility=Visibility.READER,
            )
        ]
    )

    assert ConflictResolverOutput.model_validate_json(output.model_dump_json()) == output


def test_state_manager_output_round_trips_state_diff_schema():
    output = StateManagerOutput(
        state_diff=StateDiff(id="diff_0001", turn=1, changes=[]),
        rejected_changes=[],
    )

    assert StateManagerOutput.model_validate_json(output.model_dump_json()) == output


def test_pipeline_build_diff_output_round_trips():
    output = BuildDiffOutput(diff=StateDiff(id="diff_0001", turn=1, changes=[]))

    assert BuildDiffOutput.model_validate_json(output.model_dump_json()) == output
