import pytest

from living_narrative.export_replay import NoReplayableTurnsError, assemble_replay


def test_applied_turns_without_review_yaml_are_body_turns(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 1, status="applied", narration="turn one text")

    content = assemble_replay(runs_dir, style="novel")

    assert "turn one text" in content


def test_applied_turns_assembled_in_ascending_turn_order(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    for n in (3, 1, 2):
        write_turn_dir(runs_dir, n, narration=f"body {n}")

    content = assemble_replay(runs_dir, style="novel")

    assert content.index("body 1") < content.index("body 2") < content.index("body 3")


def test_novel_style_has_no_headers_or_annotations(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(
        runs_dir,
        1,
        narration="prose body",
        interventions=[{"type": "world_directive", "target": {"kind": "world"}, "content": "x"}],
    )

    content = assemble_replay(runs_dir, style="novel")

    assert "prose body" in content
    assert "ターン" not in content
    assert "介入" not in content


def test_log_style_includes_turn_heading_and_summaries_in_order(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(
        runs_dir,
        1,
        narration="prose body",
        interventions=[
            {
                "type": "character_directive",
                "target": {"kind": "character", "id": "char_001"},
                "content": "振り返る",
            }
        ],
        events=[
            {
                "id": "event_0001",
                "turn": 1,
                "type": "x",
                "text": "reader visible event",
                "visibility": "reader",
                "roll_ids": ["roll_0001"],
            }
        ],
        rolls=[{"id": "roll_0001", "type": "dice", "result": 5}],
        diff_changes=[
            {"target": "world", "op": "set", "path": "summary", "value": "v", "visibility": "canon"}
        ],
    )

    content = assemble_replay(runs_dir, style="log")

    assert (
        content.index("ターン 1")
        < content.index("介入")
        < content.index("ロール")
        < content.index("適用diff")
        < content.index("prose body")
    )


def test_pending_review_turn_is_a_gap_in_log_style(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 3, narration="before")
    write_turn_dir(runs_dir, 4, status="stopped_for_review", narration="")
    write_turn_dir(runs_dir, 5, narration="after")

    content = assemble_replay(runs_dir, style="log")

    assert "before" in content
    assert "after" in content
    assert "未解決" in content
    assert content.index("before") < content.index("未解決") < content.index("after")


def test_pending_review_turn_is_omitted_without_placeholder_in_novel_style(
    tmp_path, write_turn_dir
):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 3, narration="before")
    write_turn_dir(runs_dir, 4, status="stopped_for_review", narration="hidden text")
    write_turn_dir(runs_dir, 5, narration="after")

    content = assemble_replay(runs_dir, style="novel")

    assert "before" in content
    assert "after" in content
    assert "hidden text" not in content
    assert "未解決" not in content


def test_reject_all_turn_is_a_gap_in_log_style(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 3, narration="before")
    write_turn_dir(runs_dir, 4, narration="rejected text", review_decision="reject_all")
    write_turn_dir(runs_dir, 5, narration="after")

    content = assemble_replay(runs_dir, style="log")

    assert "rejected text" not in content
    assert "reject_all" in content


def test_reject_all_turn_is_omitted_without_placeholder_in_novel_style(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 3, narration="before")
    write_turn_dir(runs_dir, 4, narration="rejected text", review_decision="reject_all")
    write_turn_dir(runs_dir, 5, narration="after")

    content = assemble_replay(runs_dir, style="novel")

    assert "rejected text" not in content
    assert "reject_all" not in content
    assert content.index("before") < content.index("after")


def test_applied_turn_with_non_reject_all_review_decision_is_a_body_turn(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 1, narration="partially reviewed body", review_decision="partial")

    content = assemble_replay(runs_dir, style="novel")

    assert "partially reviewed body" in content


def test_rerun_gives_byte_identical_output_across_repeated_calls(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 1, narration="a")
    write_turn_dir(runs_dir, 2, narration="b")

    first = assemble_replay(runs_dir, style="log")
    second = assemble_replay(runs_dir, style="log")

    assert first == second


def test_rolls_reachable_only_from_gm_only_events_are_excluded(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(
        runs_dir,
        1,
        narration="body",
        events=[
            {
                "id": "event_0001",
                "turn": 1,
                "type": "x",
                "text": "secret event",
                "visibility": "gm_only",
                "roll_ids": ["roll_0001"],
            }
        ],
        rolls=[{"id": "roll_0001", "type": "dice", "result": 99}],
    )

    content = assemble_replay(runs_dir, style="log")

    assert "99" not in content
    assert "ロール" not in content


def test_no_replayable_turns_raises(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    with pytest.raises(NoReplayableTurnsError):
        assemble_replay(runs_dir, style="novel")


def test_all_turns_reject_all_raises(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 1, narration="x", review_decision="reject_all")

    with pytest.raises(NoReplayableTurnsError):
        assemble_replay(runs_dir, style="novel")
