from living_narrative.export_replay.outline import (
    build_outline,
    narration_by_turn_from_records,
    render_outline_markdown,
)
from living_narrative.export_replay.reconstruction import (
    KeyEvent,
    SceneRecord,
    SessionReconstruction,
    TurningPoint,
)


def _narration(*turns: int) -> dict[int, str]:
    return {turn: f"ターン{turn}の地文" for turn in turns}


def test_short_scene_is_a_single_chapter():
    scene = SceneRecord(
        id="scene_001",
        location="駅",
        mood="静寂",
        summary="静かな夜",
        start_turn=1,
        end_turn=5,
        key_events=[
            KeyEvent(turn=3, type="threat_stage", text="足音が近づく", visibility="reader")
        ],
    )
    reconstruction = SessionReconstruction(
        scenes=[scene],
        turning_points=[TurningPoint(turn=3, kind="threat_stage", description="足音が近づく")],
    )

    outline = build_outline(reconstruction, _narration(1, 2, 3, 4, 5))

    assert len(outline.chapters) == 1
    chapter = outline.chapters[0]
    assert chapter.start_turn == 1
    assert chapter.end_turn == 5
    assert chapter.narration_texts == [f"ターン{t}の地文" for t in range(1, 6)]


def test_long_scene_splits_at_interior_turning_point():
    scene = SceneRecord(
        id="scene_001",
        location="駅",
        mood="静寂",
        summary="長い夜",
        start_turn=1,
        end_turn=12,
        key_events=[KeyEvent(turn=6, type="threat_stage", text="脅威が迫る", visibility="reader")],
    )
    reconstruction = SessionReconstruction(
        scenes=[scene],
        turning_points=[TurningPoint(turn=6, kind="threat_stage", description="脅威が迫る")],
    )

    outline = build_outline(reconstruction, _narration(*range(1, 13)))

    assert len(outline.chapters) == 2
    first, second = outline.chapters
    assert (first.start_turn, first.end_turn) == (1, 5)
    assert (second.start_turn, second.end_turn) == (6, 12)
    # contiguous, no gaps/overlaps, and covers the whole scene
    assert first.end_turn + 1 == second.start_turn
    assert second.title == "駅 — 脅威が迫る"


def test_long_scene_with_no_interior_turning_point_stays_one_chapter():
    scene = SceneRecord(
        id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=12
    )
    reconstruction = SessionReconstruction(scenes=[scene], turning_points=[])

    outline = build_outline(reconstruction, _narration(*range(1, 13)))

    assert len(outline.chapters) == 1
    assert (outline.chapters[0].start_turn, outline.chapters[0].end_turn) == (1, 12)


def test_split_candidate_too_close_to_scene_start_is_skipped():
    # A turning point at turn 2 would close a 1-turn segment (< _MIN_CHAPTER_TURNS) — skipped.
    scene = SceneRecord(
        id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=10
    )
    reconstruction = SessionReconstruction(
        scenes=[scene],
        turning_points=[
            TurningPoint(turn=2, kind="threat_stage", description="早すぎる転換点"),
            TurningPoint(turn=7, kind="threat_stage", description="妥当な転換点"),
        ],
    )

    outline = build_outline(reconstruction, _narration(*range(1, 11)))

    assert [(c.start_turn, c.end_turn) for c in outline.chapters] == [(1, 6), (7, 10)]
    assert outline.chapters[1].title == "駅 — 妥当な転換点"


def test_title_falls_back_to_key_event_when_chapter_start_has_no_turning_point():
    # scene_001's assumed start (turn 1) has no turning point landing on it.
    scene = SceneRecord(
        id="scene_001",
        location="駅",
        mood="",
        summary="",
        start_turn=1,
        end_turn=3,
        key_events=[
            KeyEvent(turn=2, type="reveal_control", text="人影が見えた", visibility="reader")
        ],
    )
    reconstruction = SessionReconstruction(scenes=[scene], turning_points=[])

    outline = build_outline(reconstruction, _narration(1, 2, 3))

    assert outline.chapters[0].title == "駅 — 人影が見えた"


def test_title_falls_back_to_bare_location_when_no_events_or_turning_points():
    scene = SceneRecord(
        id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=2
    )
    reconstruction = SessionReconstruction(scenes=[scene], turning_points=[])

    outline = build_outline(reconstruction, _narration(1, 2))

    assert outline.chapters[0].title == "駅"


def test_key_events_are_scoped_to_their_chapters_turn_range():
    scene = SceneRecord(
        id="scene_001",
        location="駅",
        mood="",
        summary="",
        start_turn=1,
        end_turn=12,
        key_events=[
            KeyEvent(turn=2, type="reveal_control", text="前半の出来事", visibility="reader"),
            KeyEvent(turn=6, type="threat_stage", text="転換点そのもの", visibility="reader"),
            KeyEvent(turn=9, type="reveal_control", text="後半の出来事", visibility="reader"),
        ],
    )
    reconstruction = SessionReconstruction(
        scenes=[scene],
        turning_points=[TurningPoint(turn=6, kind="threat_stage", description="転換点そのもの")],
    )

    outline = build_outline(reconstruction, _narration(*range(1, 13)))

    first, second = outline.chapters
    assert [e.text for e in first.key_events] == ["前半の出来事"]
    assert [e.text for e in second.key_events] == ["転換点そのもの", "後半の出来事"]


def test_chapter_indices_are_sequential_across_scenes():
    scene_1 = SceneRecord(
        id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=2
    )
    scene_2 = SceneRecord(
        id="scene_002", location="地下ホーム", mood="", summary="", start_turn=3, end_turn=None
    )
    reconstruction = SessionReconstruction(scenes=[scene_1, scene_2], turning_points=[])

    outline = build_outline(reconstruction, _narration(1, 2, 3, 4))

    assert [c.index for c in outline.chapters] == [1, 2]
    assert outline.chapters[1].end_turn == 4  # ongoing scene ends at the last narrated turn


def test_scene_transition_turn_is_not_duplicated_across_chapters():
    # scene_002 starts on the same turn scene_001 ends (turn 14): the transition
    # turn must stay in the outgoing scene's chapter only.
    scene_1 = SceneRecord(
        id="scene_001",
        location="駅",
        mood="",
        summary="",
        start_turn=10,
        end_turn=14,
        key_events=[
            KeyEvent(turn=14, type="scene_transition", text="追跡者が現れた", visibility="reader")
        ],
    )
    scene_2 = SceneRecord(
        id="scene_002",
        location="地下ホーム",
        mood="",
        summary="",
        start_turn=14,
        end_turn=17,
        key_events=[
            KeyEvent(turn=16, type="reveal_control", text="扉が開いた", visibility="reader")
        ],
    )
    reconstruction = SessionReconstruction(
        scenes=[scene_1, scene_2],
        turning_points=[
            TurningPoint(turn=14, kind="scene_transition", description="追跡者が現れた")
        ],
    )
    narration = _narration(*range(10, 18))

    outline = build_outline(reconstruction, narration)

    # no turn appears in two chapters
    seen: set[int] = set()
    for chapter in outline.chapters:
        turns = set(range(chapter.start_turn, chapter.end_turn + 1))
        assert not turns & seen
        seen |= turns
    # chapters together cover the whole narrated span, with no duplicated narration
    assert seen == set(range(10, 18))
    all_texts = [text for chapter in outline.chapters for text in chapter.narration_texts]
    assert all_texts == [f"ターン{t}の地文" for t in range(10, 18)]
    first, second = outline.chapters
    assert (first.start_turn, first.end_turn) == (10, 14)
    assert (second.start_turn, second.end_turn) == (15, 17)


def test_incoming_scene_fully_shadowed_by_outgoing_chapter_is_dropped():
    # degenerate: scene_002 spans only the transition turn — chapter dropped,
    # its key_events attach to the previous chapter.
    scene_1 = SceneRecord(
        id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=3
    )
    scene_2 = SceneRecord(
        id="scene_002",
        location="地下ホーム",
        mood="",
        summary="",
        start_turn=3,
        end_turn=3,
        key_events=[
            KeyEvent(turn=3, type="scene_transition", text="転落", visibility="reader")
        ],
    )
    reconstruction = SessionReconstruction(scenes=[scene_1, scene_2], turning_points=[])

    outline = build_outline(reconstruction, _narration(1, 2, 3))

    assert len(outline.chapters) == 1
    assert (outline.chapters[0].start_turn, outline.chapters[0].end_turn) == (1, 3)
    assert [e.text for e in outline.chapters[0].key_events] == ["転落"]


def test_build_outline_is_deterministic():
    scene = SceneRecord(
        id="scene_001",
        location="駅",
        mood="",
        summary="",
        start_turn=1,
        end_turn=12,
        key_events=[KeyEvent(turn=6, type="threat_stage", text="脅威が迫る", visibility="reader")],
    )
    reconstruction = SessionReconstruction(
        scenes=[scene],
        turning_points=[TurningPoint(turn=6, kind="threat_stage", description="脅威が迫る")],
    )
    narration = _narration(*range(1, 13))

    first = build_outline(reconstruction, narration)
    second = build_outline(reconstruction, narration)

    assert first.model_dump() == second.model_dump()


def test_render_outline_markdown_includes_titles_and_turn_ranges():
    scene = SceneRecord(
        id="scene_001", location="駅", mood="", summary="", start_turn=1, end_turn=2
    )
    reconstruction = SessionReconstruction(scenes=[scene], turning_points=[])

    outline = build_outline(reconstruction, _narration(1, 2))
    markdown = render_outline_markdown(outline)

    assert "# 章立て" in markdown
    assert "第1章: 駅" in markdown
    assert "ターン: 1〜2" in markdown


def test_narration_by_turn_from_records_skips_non_body_turns():
    from living_narrative.export_replay.loader import TurnRecord

    records = [
        TurnRecord(turn=1, status="applied", narration_body="本文1"),
        TurnRecord(turn=2, status="failed", narration_body=None),
        TurnRecord(turn=3, status="applied", narration_body="本文3", review_decision="reject_all"),
    ]

    assert narration_by_turn_from_records(records) == {1: "本文1"}
