from living_narrative.safety.leak_check import leak_checker, llm_leak_evaluation
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import (
    CharacterState,
    Event,
    GmVaultEntry,
    HiddenFact,
    ReaderStateEntry,
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
            characters=[
                CharacterState(
                    id="char_001",
                    name="A",
                    role="r",
                    private_mind=["private exact"],
                    secrets=["secret exact"],
                )
            ],
            scenes=[
                SceneState(
                    id="scene_001",
                    location="loc",
                    time="now",
                    hidden_facts=[
                        HiddenFact(
                            id="fact_001",
                            text="hidden exact",
                            visibility=Visibility.GM_ONLY,
                        )
                    ],
                )
            ],
            gm_vault=[GmVaultEntry(id="gm_vault_001", text="truth")],
        )
    )


def test_gm_vault_fact_id_leak_is_error():
    findings = leak_checker(
        _context(), "gm_vault_001 appears", [], StateDiff(id="diff_0001", turn=1)
    )

    assert findings[0].severity == "error"
    assert findings[0].related_ids == ["gm_vault_001"]


def test_hidden_fact_text_leak_is_error():
    findings = leak_checker(_context(), "hidden exact", [], StateDiff(id="diff_0001", turn=1))

    assert findings[0].severity == "error"


def test_reveal_now_reader_state_add_is_allowed():
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="reader_state",
                op="add",
                path="",
                visibility=Visibility.READER,
                source_event="event_0001",
                value={
                    "id": "reader_state_0001",
                    "text": "hidden exact",
                    "established_turn": 1,
                    "source_event": "event_0001",
                    "disclosed_turn": 1,
                },
            )
        ],
    )

    assert leak_checker(_context(), "hidden exact", [], diff) == []


def test_existing_reader_state_text_is_allowed():
    context = _context()
    context.bundle.reader_state = [
        ReaderStateEntry(
            id="reader_state_0001",
            text="hidden exact",
            established_turn=1,
            source_event="event_0001",
            disclosed_turn=1,
        )
    ]

    assert leak_checker(context, "hidden exact", [], StateDiff(id="diff_0001", turn=1)) == []


def test_other_character_secret_in_reader_event_is_error():
    event = Event(
        id="event_0001",
        turn=1,
        type="public",
        text="secret exact",
        visibility=Visibility.READER,
    )

    findings = leak_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert findings[0].severity == "error"


def test_paraphrased_leak_is_not_mechanically_detected():
    findings = leak_checker(
        _context(),
        "the concealed fact is implied",
        [],
        StateDiff(id="diff_0001", turn=1),
    )

    assert findings == []


def test_undisclosed_inner_reaction_tagged_reader_is_error():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_inner_reaction",
        text="inner thought exact",
        visibility=Visibility.READER,
    )

    findings = leak_checker(_context(), "", [event], StateDiff(id="diff_0001", turn=1))

    assert findings[0].severity == "error"
    assert findings[0].related_ids == ["event_0001"]


def test_disclosed_inner_reaction_tagged_reader_is_allowed():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_inner_reaction",
        text="inner thought exact",
        visibility=Visibility.READER,
    )
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="reader_state",
                op="add",
                path="",
                visibility=Visibility.READER,
                source_event="event_0001",
                value={
                    "id": "reader_state_0001",
                    "text": "inner thought exact",
                    "established_turn": 1,
                    "source_event": "event_0001",
                    "disclosed_turn": 1,
                },
            )
        ],
    )

    assert leak_checker(_context(), "", [event], diff) == []


def test_inner_reaction_tagged_character_not_quoted_is_no_error():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_inner_reaction",
        text="inner thought exact",
        visibility=Visibility.CHARACTER,
    )

    findings = leak_checker(
        _context(), "unrelated narration text", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings == []


def test_inner_reaction_tagged_character_quoted_verbatim_is_error():
    event = Event(
        id="event_0001",
        turn=1,
        type="character_inner_reaction",
        text="inner thought exact",
        visibility=Visibility.CHARACTER,
    )

    findings = leak_checker(
        _context(), "inner thought exact", [event], StateDiff(id="diff_0001", turn=1)
    )

    assert findings[0].severity == "error"
    assert findings[0].related_ids == ["event_0001"]


def test_llm_leak_evaluation_is_warn_when_enabled():
    assert llm_leak_evaluation(True)[0].severity == "warn"
