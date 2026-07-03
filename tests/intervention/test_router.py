from living_narrative.intervention.router import character_directives_for, resolve_tone_control
from living_narrative.state.models import CharacterState, SceneState, WorldState, WorldStateBundle


def _bundle() -> WorldStateBundle:
    return WorldStateBundle(
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
                active_characters=["char_001", "char_002"],
            )
        ],
    )


def test_character_directive_reaches_only_its_target():
    interventions = [
        {"type": "character_directive", "target": {"kind": "character", "id": "char_001"}}
    ]

    assert character_directives_for(interventions, "char_001", _bundle()) == interventions
    assert character_directives_for(interventions, "char_002", _bundle()) == []


def test_scene_directive_broadcasts_to_the_scene():
    interventions = [{"type": "scene_directive", "target": {"kind": "scene", "id": "scene_001"}}]

    assert character_directives_for(interventions, "char_001", _bundle()) == interventions
    assert character_directives_for(interventions, "char_002", _bundle()) == interventions


def test_unhandled_types_are_broadcast_as_constraints():
    interventions = [{"type": "pacing_control", "target": {"kind": "scene"}}]

    assert character_directives_for(interventions, "char_001", _bundle()) == interventions


def test_stop_condition_never_reaches_a_character_context():
    interventions = [{"type": "stop_condition", "target": {"kind": "world"}}]

    assert character_directives_for(interventions, "char_001", _bundle()) == []


def test_world_directive_does_not_leak_into_character_context():
    interventions = [{"type": "world_directive", "target": {"kind": "world"}}]

    assert character_directives_for(interventions, "char_001", _bundle()) == []


def test_resolve_tone_control_prefers_explicit_override():
    interventions = [{"type": "tone_control", "content": "serious"}]

    assert resolve_tone_control(interventions, "playful") == "playful"


def test_resolve_tone_control_falls_back_to_the_latest_intervention():
    interventions = [
        {"type": "tone_control", "content": "serious"},
        {"type": "tone_control", "content": "urgent"},
    ]

    assert resolve_tone_control(interventions) == "urgent"


def test_resolve_tone_control_is_none_without_override_or_intervention():
    assert resolve_tone_control([]) is None
