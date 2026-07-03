from living_narrative.intervention.direct_input import build_intervention_from_direct_input
from living_narrative.intervention.permissions import PermissionRejection
from living_narrative.intervention.schema import Intervention


def _ids():
    counter = 0

    def allocate():
        nonlocal counter
        counter += 1
        return f"int_{counter:04d}"

    return allocate


def test_direct_input_builds_a_validated_intervention_without_an_llm_call():
    outcome = build_intervention_from_direct_input(
        {
            "type": "world_directive",
            "target": {"kind": "world"},
            "content": "雨を降らせる",
            "constraints": {},
            "visibility": "reader",
        },
        turn=3,
        user_role="full_gm",
        allocate_id=_ids(),
    )

    assert isinstance(outcome, Intervention)
    assert outcome.id == "int_0001"
    assert outcome.turn == 3
    assert outcome.user_role == "full_gm"


def test_direct_input_applies_the_permission_hook():
    outcome = build_intervention_from_direct_input(
        {
            "type": "canon_edit",
            "target": {"kind": "canon"},
            "content": "新しい事実",
            "visibility": "canon",
        },
        turn=1,
        user_role="watcher",
        allocate_id=_ids(),
    )

    assert isinstance(outcome, PermissionRejection)


def test_caller_supplied_id_turn_and_user_role_are_ignored():
    outcome = build_intervention_from_direct_input(
        {
            "id": "int_9999",
            "turn": 999,
            "user_role": "god",
            "type": "scene_directive",
            "target": {"kind": "scene", "id": "scene_001"},
            "content": "緊張感を高める",
            "visibility": "scene",
        },
        turn=5,
        user_role="author",
        allocate_id=_ids(),
    )

    assert isinstance(outcome, Intervention)
    assert outcome.id == "int_0001"
    assert outcome.turn == 5
    assert outcome.user_role == "author"
