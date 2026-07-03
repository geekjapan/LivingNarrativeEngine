from living_narrative.agents.models import (
    ActionCandidate,
    CharacterAgentOutput,
    ConflictResolverOutput,
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
