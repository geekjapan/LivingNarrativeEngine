import pytest
import yaml

from living_narrative.export_replay import (
    ReconstructionError,
    SessionReconstruction,
    reconstruct_session,
    render_scenes_markdown,
)


def _add_scene(project_path, scene_id, *, location, mood="", summary="", status="active"):
    state_dir = project_path.parent / "workspace" / "state"
    scene = {
        "id": scene_id,
        "location": location,
        "time": "夜",
        "active_characters": [],
        "mood": mood,
        "status": status,
        "summary": summary,
    }
    (state_dir / "scenes" / f"{scene_id}.yaml").write_text(
        yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8"
    )


def _write_transition_project(tmp_path, build_project, write_turn_dir):
    """Two scenes, a transition at turn 2, and every excluded/included event kind."""
    project_path = build_project(tmp_path, scene_status="ended")
    _add_scene(project_path, "scene_002", location="次の場所", mood="警戒", summary="逃走中")

    runs_dir = project_path.parent / "workspace" / "runs"
    write_turn_dir(
        runs_dir,
        1,
        narration="turn one",
        events=[
            {
                "id": "event_0001",
                "turn": 1,
                "type": "threat_stage",
                "text": "足音が近づく",
                "visibility": "reader",
                "effects": {"threat_id": "threat_001", "stage_at": 50},
            },
            {
                "id": "event_0002",
                "turn": 1,
                "type": "threat_pressure",
                "text": "圧力上昇",
                "visibility": "gm_only",
                "effects": {"threat_id": "threat_001", "pressure": 50},
            },
            {
                "id": "event_0003",
                "turn": 1,
                "type": "background_event",
                "text": "静かな時間が流れる",
                "visibility": "reader",
                "effects": {},
            },
        ],
    )
    write_turn_dir(
        runs_dir,
        2,
        narration="turn two",
        events=[
            {
                "id": "event_0004",
                "turn": 2,
                "type": "event_injection",
                "text": "追跡者が姿を現す",
                "visibility": "reader",
                "effects": {"scene_transition": {"end": "scene_001", "start": "scene_002"}},
            },
            {
                "id": "event_0005",
                "turn": 2,
                "type": "thread_update",
                "text": "伏線『足跡』を開始",
                "visibility": "gm_only",
                "effects": {"thread_id": "thread_001", "action": "open"},
            },
        ],
        diff_changes=[
            {
                "target": "scene",
                "id": "scene_001",
                "op": "set",
                "path": "status",
                "value": "ended",
                "visibility": "canon",
            },
            {
                "target": "scene",
                "id": "scene_002",
                "op": "set",
                "path": "status",
                "value": "active",
                "visibility": "canon",
            },
        ],
    )
    return project_path


def test_two_scenes_with_correct_turn_ranges(tmp_path, build_project, write_turn_dir):
    project_path = _write_transition_project(tmp_path, build_project, write_turn_dir)

    result = reconstruct_session(project_path)

    assert [s.id for s in result.scenes] == ["scene_001", "scene_002"]
    scene_1, scene_2 = result.scenes
    assert scene_1.start_turn == 1
    assert scene_1.end_turn == 2
    assert scene_1.location == "駅"
    assert scene_2.start_turn == 2
    assert scene_2.end_turn is None
    assert scene_2.location == "次の場所"
    assert scene_2.summary == "逃走中"


def test_key_events_include_transition_and_threat_stage_exclude_noise(
    tmp_path, build_project, write_turn_dir
):
    project_path = _write_transition_project(tmp_path, build_project, write_turn_dir)

    result = reconstruct_session(project_path)

    scene_1, scene_2 = result.scenes
    kinds = {event.type for event in scene_1.key_events}
    assert kinds == {"threat_stage", "scene_transition"}
    texts = {event.text for event in scene_1.key_events}
    assert texts == {"足音が近づく", "追跡者が姿を現す"}
    # background_event / threat_pressure never show up anywhere
    all_key_event_texts = {event.text for scene in result.scenes for event in scene.key_events}
    assert "静かな時間が流れる" not in all_key_event_texts
    assert "圧力上昇" not in all_key_event_texts
    assert scene_2.key_events == []


def test_turning_points_capture_threat_stage_and_scene_transition(
    tmp_path, build_project, write_turn_dir
):
    project_path = _write_transition_project(tmp_path, build_project, write_turn_dir)

    result = reconstruct_session(project_path)

    turning = {(p.turn, p.kind) for p in result.turning_points}
    assert (1, "threat_stage") in turning
    assert (2, "scene_transition") in turning


def test_reader_mode_drops_gm_only_thread_update(tmp_path, build_project, write_turn_dir):
    project_path = _write_transition_project(tmp_path, build_project, write_turn_dir)

    reader = reconstruct_session(project_path)
    gm = reconstruct_session(project_path, include_gm=True)

    reader_kinds = {event.type for scene in reader.scenes for event in scene.key_events}
    gm_kinds = {event.type for scene in gm.scenes for event in scene.key_events}
    assert "thread_update" not in reader_kinds
    assert "thread_update" in gm_kinds


def test_scenes_markdown_renders(tmp_path, build_project, write_turn_dir):
    project_path = _write_transition_project(tmp_path, build_project, write_turn_dir)
    result = reconstruct_session(project_path)

    markdown = render_scenes_markdown(result)

    assert "scene_001" in markdown
    assert "scene_002" in markdown
    assert "駅" in markdown
    assert "次の場所" in markdown
    assert "threat_stage" in markdown
    assert "転換点" in markdown


def test_scenes_yaml_round_trips(tmp_path, build_project, write_turn_dir):
    project_path = _write_transition_project(tmp_path, build_project, write_turn_dir)
    result = reconstruct_session(project_path)

    dumped = yaml.safe_dump(result.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
    loaded = yaml.safe_load(dumped)
    rebuilt = SessionReconstruction(**loaded)

    assert rebuilt.model_dump() == result.model_dump()


def test_empty_project_has_one_scene_and_no_crash(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = reconstruct_session(project_path)

    assert len(result.scenes) == 1
    scene = result.scenes[0]
    assert scene.id == "scene_001"
    assert scene.start_turn == 1
    assert scene.end_turn is None
    assert scene.key_events == []
    assert result.turning_points == []


def test_project_not_found_raises(tmp_path):
    missing = tmp_path / "does_not_exist" / "project.yaml"

    with pytest.raises(ReconstructionError):
        reconstruct_session(missing)
