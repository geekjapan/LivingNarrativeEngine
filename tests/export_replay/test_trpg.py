from living_narrative.export_replay.loader import load_turn_records
from living_narrative.export_replay.reconstruction import SceneRecord, SessionReconstruction
from living_narrative.export_replay.trpg import render_trpg_replay


def _reconstruction(*scenes: SceneRecord) -> SessionReconstruction:
    return SessionReconstruction(scenes=list(scenes), turning_points=[])


def test_trpg_replay_includes_header_rolls_interventions_and_scene_heading(
    tmp_path, write_turn_dir
):
    runs_dir = tmp_path / "runs"
    write_turn_dir(
        runs_dir,
        1,
        narration="prose body",
        interventions=[
            {
                "type": "world_directive",
                "target": {"kind": "world"},
                "content": "雨が降り始める",
            }
        ],
        rolls=[
            {
                "id": "roll_0001",
                "turn": 1,
                "type": "dice",
                "label": "気づく判定",
                "dice": {"notation": "2d6", "target": 7},
                "result": 8,
            }
        ],
    )
    records = load_turn_records(runs_dir)
    reconstruction = _reconstruction(
        SceneRecord(id="scene_001", location="駅", mood="緊張", summary="", start_turn=1)
    )

    content = render_trpg_replay(records, reconstruction)

    assert "GM出力" in content
    assert content.index("シーン: 駅") < content.index("ターン 1")
    assert (
        content.index("ロール欄")
        < content.index("気づく判定: 2d6 → 8")
        < content.index("介入欄")
        < content.index("GM介入: world_directive — 雨が降り始める")
        < content.index("prose body")
    )


def test_trpg_replay_shows_gm_only_rolls_unlike_reader_log_style(tmp_path, write_turn_dir):
    """Unlike ``render.py``'s ``log`` style, --trpg is a GM artifact: it must not filter
    rolls down to only those reachable from a reader-visible event (D121)."""
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
    records = load_turn_records(runs_dir)
    reconstruction = _reconstruction(
        SceneRecord(id="scene_001", location="駅", mood="", summary="", start_turn=1)
    )

    content = render_trpg_replay(records, reconstruction)

    assert "99" in content
    assert "ロール欄" in content


def test_trpg_replay_inserts_scene_heading_on_transition(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 1, narration="turn one")
    write_turn_dir(runs_dir, 2, narration="turn two")
    records = load_turn_records(runs_dir)
    reconstruction = _reconstruction(
        SceneRecord(id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=1),
        SceneRecord(id="scene_002", location="トンネル", mood="", summary="", start_turn=2),
    )

    content = render_trpg_replay(records, reconstruction)

    assert (
        content.index("シーン: 駅")
        < content.index("ターン 1")
        < content.index("シーン: トンネル")
        < content.index("ターン 2")
    )


def test_trpg_replay_gap_turn_uses_h3_heading(tmp_path, write_turn_dir):
    runs_dir = tmp_path / "runs"
    write_turn_dir(runs_dir, 1, narration="before")
    write_turn_dir(runs_dir, 2, status="stopped_for_review", narration="")
    write_turn_dir(runs_dir, 3, narration="after")
    records = load_turn_records(runs_dir)
    reconstruction = _reconstruction(
        SceneRecord(id="scene_001", location="駅", mood="", summary="", start_turn=1)
    )

    content = render_trpg_replay(records, reconstruction)

    assert "### ターン 2 (未解決: レビューのため停止)" in content


def test_trpg_replay_raises_when_no_turns_have_run(tmp_path):
    from living_narrative.export_replay.assemble import NoReplayableTurnsError

    reconstruction = _reconstruction()

    try:
        render_trpg_replay([], reconstruction)
        raise AssertionError("expected NoReplayableTurnsError")
    except NoReplayableTurnsError:
        pass
