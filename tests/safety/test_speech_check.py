"""Issue 012: speech-register checker -- warns (never blocks) when a character's dialogue
contains one of that character's own forbidden_terms (e.g. the wrong first-person pronoun)."""

from living_narrative.safety.speech_check import speech_register_checker
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import (
    CharacterState,
    Event,
    SpeechProfile,
    Visibility,
    WorldState,
    WorldStateBundle,
)


class Context:
    bundle: WorldStateBundle

    def __init__(self, bundle):
        self.bundle = bundle


def _context(*, speech: SpeechProfile | None = None) -> Context:
    return Context(
        WorldStateBundle(
            world=WorldState(id="world_001", name="World", summary=""),
            characters=[
                CharacterState(
                    id="char_001",
                    name="リナ",
                    role="主人公",
                    speech=speech or SpeechProfile(first_person="私", forbidden_terms=["僕", "俺"]),
                )
            ],
        )
    )


def _event(text: str, event_type: str = "character_dialogue", **effects) -> Event:
    return Event(
        id="event_0001",
        turn=1,
        type=event_type,
        text=text,
        visibility=Visibility.READER,
        effects=effects,
    )


def test_forbidden_term_in_dialogue_is_flagged_as_warn_with_related_event_id():
    event = _event("僕はここにいる", character_id="char_001")

    findings = speech_register_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert len(findings) == 1
    assert findings[0].checker == "speech_register_check"
    assert findings[0].severity == "warn"
    assert findings[0].related_ids == ["event_0001"]
    assert "リナ" in findings[0].message
    assert "僕" in findings[0].message


def test_clean_dialogue_is_silent():
    event = _event("私はここにいる", character_id="char_001")

    findings = speech_register_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert findings == []


def test_non_dialogue_event_with_forbidden_term_is_silent():
    event = _event("僕はここにいる", event_type="character_action", character_id="char_001")

    findings = speech_register_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert findings == []


def test_character_with_no_speech_profile_is_never_flagged():
    event = _event("僕はここにいる", character_id="char_001")

    findings = speech_register_checker(
        _context(speech=SpeechProfile()), "", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_substring_match_inside_a_larger_word_is_still_flagged():
    # Design decision (issue 012): forbidden_terms are matched as plain substrings, not
    # tokenized words. Japanese has no whitespace word boundaries, so a stricter
    # word-boundary match isn't meaningfully definable here; a term appearing inside a
    # larger word is an acceptable false-positive trade-off for catching real pronoun slips.
    event = _event("僕僕丸(あだ名)が笑った", character_id="char_001")

    findings = speech_register_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert len(findings) == 1


def test_unknown_character_id_is_silent():
    event = _event("僕はここにいる", character_id="char_999")

    findings = speech_register_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert findings == []
