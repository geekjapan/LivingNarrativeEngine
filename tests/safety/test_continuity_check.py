from living_narrative.safety.continuity_check import continuity_checker, llm_canon_evaluation
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import (
    CharacterState,
    Event,
    SceneState,
    Visibility,
    WorldState,
    WorldStateBundle,
)


class Context:
    bundle: WorldStateBundle

    def __init__(self, bundle):
        self.bundle = bundle


def _context() -> Context:
    return Context(
        WorldStateBundle(
            world=WorldState(id="world_001", name="World", summary=""),
            characters=[CharacterState(id="char_001", name="A", role="r")],
            scenes=[SceneState(id="scene_001", location="loc", time="now", active_characters=[])],
        )
    )


def test_absent_character_action_is_error():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_action",
        text="acts",
        visibility=Visibility.READER,
        effects={"character_id": "char_001"},
    )

    findings = continuity_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert findings[0].severity == "error"


def test_non_present_character_dialogue_is_error():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_dialogue",
        text="speaks",
        visibility=Visibility.READER,
        effects={"character_id": "char_001"},
    )

    findings = continuity_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert any("spoke" in finding.message for finding in findings)


def test_knowledge_add_without_source_event_is_error():
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="character",
                id="char_001",
                op="add",
                path="knowledge.knows",
                value="x",
                visibility=Visibility.CHARACTER,
            )
        ],
    )

    findings = continuity_checker(_context(), "", [], diff)

    assert findings[0].severity == "error"


def test_llm_canon_evaluation_is_warn_when_enabled():
    assert llm_canon_evaluation(True)[0].severity == "warn"
