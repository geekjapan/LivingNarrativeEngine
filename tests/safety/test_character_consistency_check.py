"""Issue 016: character-consistency checker -- warns (never blocks) when a character's own
dialogue/action text mentions something in their ``knowledge.does_not_know``, or discloses one
of their own ``secrets`` in a reader-visible event."""

from living_narrative.safety.character_consistency_check import character_consistency_checker
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import (
    CharacterKnowledge,
    CharacterState,
    Event,
    Visibility,
    WorldState,
    WorldStateBundle,
)


class Context:
    bundle: WorldStateBundle

    def __init__(self, bundle):
        self.bundle = bundle


def _character(
    character_id: str,
    name: str,
    *,
    does_not_know: list[str] | None = None,
    secrets: list[str] | None = None,
) -> CharacterState:
    return CharacterState(
        id=character_id,
        name=name,
        role="役",
        knowledge=CharacterKnowledge(does_not_know=does_not_know or []),
        secrets=secrets or [],
    )


def _context(*characters: CharacterState) -> Context:
    return Context(
        WorldStateBundle(
            world=WorldState(id="world_001", name="World", summary=""),
            characters=list(characters),
        )
    )


def _event(
    text: str,
    *,
    event_type: str = "character_dialogue",
    visibility: Visibility = Visibility.READER,
    character_id: str = "char_001",
) -> Event:
    return Event(
        id="event_0001",
        turn=1,
        type=event_type,
        text=text,
        visibility=visibility,
        effects={"character_id": character_id},
    )


def test_know_violation_is_flagged_as_warn_with_related_event_id():
    character = _character("char_001", "リナ", does_not_know=["封印施設"])
    event = _event("封印施設のことは聞いたことがある")

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert len(findings) == 1
    assert findings[0].checker == "character_consistency_check"
    assert findings[0].severity == "warn"
    assert findings[0].related_ids == ["event_0001"]
    assert "リナ" in findings[0].message
    assert "封印施設" in findings[0].message


def test_know_violation_fires_for_character_action_events_too():
    character = _character("char_001", "リナ", does_not_know=["封印施設"])
    event = _event("封印施設に向かって歩き出した", event_type="character_action")

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert len(findings) == 1


def test_other_characters_does_not_know_is_ignored():
    speaker = _character("char_001", "リナ", does_not_know=[])
    other = _character("char_002", "カイ", does_not_know=["ミラの正体"])
    event = _event("ミラの正体について話した", character_id="char_001")

    findings = character_consistency_checker(
        _context(speaker, other), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_clean_dialogue_is_silent():
    character = _character("char_001", "リナ", does_not_know=["封印施設"])
    event = _event("今日は静かな夜だ")

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_secret_disclosed_in_reader_visible_dialogue_is_flagged():
    character = _character("char_001", "カイ", secrets=["幼い頃の記憶"])
    event = _event("幼い頃の記憶がよみがえる", visibility=Visibility.READER)

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert len(findings) == 1
    assert findings[0].checker == "character_consistency_check"
    assert findings[0].severity == "warn"
    assert "幼い頃の記憶" in findings[0].message


def test_same_secret_in_character_visibility_event_is_not_flagged():
    character = _character("char_001", "カイ", secrets=["幼い頃の記憶"])
    event = _event(
        "幼い頃の記憶がよみがえる",
        event_type="character_action",
        visibility=Visibility.CHARACTER,
    )

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_same_secret_in_gm_only_or_scene_visibility_is_not_flagged():
    character = _character("char_001", "カイ", secrets=["幼い頃の記憶"])
    events = [
        _event("幼い頃の記憶がよみがえる", visibility=Visibility.GM_ONLY),
        _event("幼い頃の記憶がよみがえる", visibility=Visibility.SCENE),
    ]

    findings = character_consistency_checker(
        _context(character), "", events, StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_empty_knowledge_and_secrets_is_never_flagged():
    character = _character("char_001", "リナ")
    event = _event("封印施設のことも幼い頃の記憶のことも話した")

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_non_speaker_event_type_is_silent():
    character = _character("char_001", "リナ", does_not_know=["封印施設"])
    event = _event("封印施設について", event_type="character_inner_reaction")

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_unknown_character_id_is_silent():
    character = _character("char_001", "リナ", does_not_know=["封印施設"])
    event = _event("封印施設のことは聞いたことがある", character_id="char_999")

    findings = character_consistency_checker(
        _context(character), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []
