from living_narrative.intervention.history import (
    append_history,
    build_history_entries,
    load_history,
    mark_superseded_by_rerun,
)
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import Event, Visibility


def _event(event_id: str, cause: str) -> Event:
    return Event(
        id=event_id,
        turn=1,
        type="world_directive",
        cause=cause,
        text="text",
        visibility=Visibility.CANON,
    )


def test_build_history_entries_traces_intervention_to_its_resulting_event():
    interventions = [{"id": "int_0042", "turn": 1, "type": "world_directive"}]
    events = [_event("event_0081", "intervention:int_0042")]
    diff = StateDiff(id="diff_0001", turn=1, changes=[])

    entries = build_history_entries(interventions, events, diff)

    assert entries[0].id == "int_0042"
    assert entries[0].source_event_ids == ["event_0081"]
    assert entries[0].diff_id is None


def test_build_history_entries_includes_diff_id_when_a_change_references_the_event():
    interventions = [{"id": "int_0001", "turn": 1, "type": "canon_edit"}]
    events = [_event("event_0002", "intervention:int_0001")]
    diff = StateDiff(
        id="diff_0001",
        turn=1,
        changes=[
            StateDiffChange(
                target="canon",
                op="add",
                value={"id": "canon_0001", "text": "x", "established_turn": 1},
                visibility=Visibility.CANON,
                source_event="event_0002",
            )
        ],
    )

    entries = build_history_entries(interventions, events, diff)

    assert entries[0].diff_id == "diff_0001"


def test_history_accumulates_across_turns_without_overwriting(tmp_path):
    path = tmp_path / "interventions.yaml"
    diff = StateDiff(id="diff_0001", turn=1, changes=[])

    turn1_entries = build_history_entries(
        [{"id": "int_0001", "turn": 1, "type": "world_directive"}], [], diff
    )
    append_history(path, turn1_entries)
    turn2_entries = build_history_entries(
        [{"id": "int_0002", "turn": 2, "type": "world_directive"}], [], diff
    )
    append_history(path, turn2_entries)

    history = load_history(path)
    assert [entry.id for entry in history.entries] == ["int_0001", "int_0002"]


def test_mark_superseded_by_rerun_flips_only_matching_entries(tmp_path):
    path = tmp_path / "interventions.yaml"
    diff = StateDiff(id="diff_0001", turn=1, changes=[])
    events = [_event("event_0001", "intervention:int_0001")]
    entries = build_history_entries([{"id": "int_0001", "turn": 1, "type": "x"}], events, diff)
    append_history(path, entries)
    append_history(
        path,
        build_history_entries(
            [{"id": "int_0002", "turn": 2, "type": "x"}],
            [_event("event_0002", "intervention:int_0002")],
            diff,
        ),
    )

    mark_superseded_by_rerun(path, {"event_0001"})

    history = load_history(path)
    by_id = {entry.id: entry for entry in history.entries}
    assert by_id["int_0001"].superseded_by_rerun is True
    assert by_id["int_0002"].superseded_by_rerun is False
