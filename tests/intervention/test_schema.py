import pytest
from pydantic import ValidationError

from living_narrative.intervention.schema import (
    DELEGATED_TYPES,
    HANDLING_STATUS,
    ROUTED_TYPES,
    UNHANDLED_TYPES,
    HandlingStatus,
    Intervention,
    InterventionTarget,
    InterventionType,
)


def _intervention(**overrides):
    data = {
        "id": "int_0001",
        "turn": 1,
        "user_role": "full_gm",
        "type": "world_directive",
        "target": {"kind": "world"},
        "content": "雨を降らせる",
        "visibility": "reader",
    }
    data.update(overrides)
    return Intervention.model_validate(data)


def test_valid_intervention_round_trips():
    intervention = _intervention()
    assert intervention.type == InterventionType.WORLD_DIRECTIVE
    assert intervention.target.kind == "world"


def test_unknown_type_is_rejected():
    with pytest.raises(ValidationError):
        _intervention(type="not_a_real_type")


def test_target_is_a_nested_model_not_flat_fields():
    intervention = _intervention(target={"kind": "character", "id": "char_001"})
    assert isinstance(intervention.target, InterventionTarget)
    assert intervention.target.id == "char_001"
    assert "target_id" not in intervention.model_dump()


def test_relationship_target_id_must_be_composite_key():
    with pytest.raises(ValidationError):
        InterventionTarget.model_validate({"kind": "relationship", "id": "char_001"})
    target = InterventionTarget.model_validate({"kind": "relationship", "id": "char_001__char_002"})
    assert target.id == "char_001__char_002"


def test_all_15_types_are_classified_in_handling_status():
    assert len(HANDLING_STATUS) == 15
    assert len(ROUTED_TYPES) == 9
    assert len(DELEGATED_TYPES) == 1
    assert len(UNHANDLED_TYPES) == 5


def test_stop_condition_is_delegated_not_routed_or_unhandled():
    assert HANDLING_STATUS[InterventionType.STOP_CONDITION] == HandlingStatus.DELEGATED
    assert InterventionType.STOP_CONDITION not in ROUTED_TYPES
    assert InterventionType.STOP_CONDITION not in UNHANDLED_TYPES


@pytest.mark.parametrize(
    "type_",
    [
        InterventionType.SCENE_DIRECTIVE,
        InterventionType.CHARACTER_DIRECTIVE,
        InterventionType.WORLD_DIRECTIVE,
        InterventionType.EVENT_INJECTION,
        InterventionType.TONE_CONTROL,
        InterventionType.REVEAL_CONTROL,
        InterventionType.DICE_ROLL_REQUEST,
        InterventionType.CANON_EDIT,
        InterventionType.HIDDEN_TRUTH_EDIT,
    ],
)
def test_the_9_routed_types_are_routed(type_):
    assert HANDLING_STATUS[type_] == HandlingStatus.ROUTED


@pytest.mark.parametrize(
    "type_",
    [
        InterventionType.PROBABILITY_BIAS,
        InterventionType.PACING_CONTROL,
        InterventionType.SCENE_PIVOT,
        InterventionType.RELATIONSHIP_EDIT,
        InterventionType.MEMORY_EDIT,
    ],
)
def test_the_5_remaining_types_are_unhandled(type_):
    assert HANDLING_STATUS[type_] == HandlingStatus.UNHANDLED
