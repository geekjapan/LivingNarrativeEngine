"""End-to-end coverage of the 9 routed intervention types + permission rejection + history."""

import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus


def _set_user_mode(project_path, user_mode: str) -> None:
    data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    data["user_mode"] = user_mode
    project_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _add_gm_vault_entry(project_path, entry_id: str, text: str) -> None:
    state_dir = project_path.parent / "workspace" / "state"
    path = state_dir / "gm_vault.yaml"
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    entries.append({"id": entry_id, "text": text})
    path.write_text(yaml.safe_dump(entries, allow_unicode=True), encoding="utf-8")


def _add_pending_scene(project_path, scene_id: str) -> None:
    state_dir = project_path.parent / "workspace" / "state"
    scene = {
        "id": scene_id,
        "location": "次の場所",
        "time": "夜",
        "active_characters": [],
        "status": "pending",
    }
    (state_dir / "scenes" / f"{scene_id}.yaml").write_text(
        yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8"
    )


def _drafts(*items):
    return list(items)


def test_intervention_yaml_records_confirmed_interventions(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "scene_directive",
                "target": {"kind": "scene", "id": "scene_001"},
                "content": "緊張感を高める",
                "visibility": "scene",
            }
        ),
    )

    intervention_file = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    assert len(intervention_file["interventions"]) == 1
    assert intervention_file["interventions"][0]["type"] == "scene_directive"
    assert intervention_file["interventions"][0]["turn"] == result.turn
    assert intervention_file["rejections"] == []


def test_permission_rejection_is_recorded_and_produces_no_state_change(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "watcher")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "canon_edit",
                "target": {"kind": "canon"},
                "content": "禁止された編集",
                "visibility": "canon",
            }
        ),
    )

    intervention_file = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    assert intervention_file["interventions"] == []
    assert len(intervention_file["rejections"]) == 1
    assert intervention_file["rejections"][0]["type"] == "canon_edit"

    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    # timeline追記とキャラクター感情/目標のdiff(Issue 006)は介入とは独立に発生しうる。
    # ここで見るのは「棄却された介入が状態変更を生まないこと」のみ。
    intervention_changes = [
        c for c in state_diff["diff"]["changes"] if c["target"] not in ("timeline", "character")
    ]
    assert intervention_changes == []


def test_character_directive_routes_only_to_the_target_character(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "character_directive",
                "target": {"kind": "character", "id": "char_001"},
                "content": "怪しい男に気づく",
                "visibility": "character",
            }
        ),
    )

    act_records = yaml.safe_load(
        (result.turn_dir / "agent_io" / "act.yaml").read_text(encoding="utf-8")
    )
    directives = act_records[0]["input_context"]["directives"]
    assert len(directives) == 1
    assert directives[0]["content"] == "怪しい男に気づく"


def test_world_directive_and_event_injection_appear_in_events(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "world_directive",
                "target": {"kind": "world"},
                "content": "雨が降り始める",
                "visibility": "reader",
            },
            {
                "type": "event_injection",
                "target": {"kind": "world"},
                "content": "見知らぬ男が現れる",
                "visibility": "reader",
            },
        ),
    )

    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    types = {event["type"] for event in events}
    assert {"world_directive", "event_injection"} <= types


def test_dice_roll_request_is_recorded_in_rolls_yaml(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "dice_roll_request",
                "target": {"kind": "roll"},
                "content": "気づくかどうか",
                "constraints": {"notation": "2d6", "target": 7},
                "visibility": "gm_only",
            }
        ),
    )

    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    assert any(roll["dice"]["notation"] == "2d6" for roll in rolls)


def test_encounter_roll_is_recorded_by_existing_pipeline_extraction(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    (state_dir / "encounters.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "encounter_001",
                    "text": "霧の中から旅人が現れる",
                    "weight": 1,
                    "visibility": "reader",
                    "scene_id": "scene_001",
                }
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = TurnPipeline().run(project_path)

    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    encounter = next(event for event in events if event["type"] == "encounter")
    roll = next(item for item in rolls if item["table"]["table"] == "encounters")
    assert encounter["text"] == "霧の中から旅人が現れる"
    assert encounter["effects"]["encounter_id"] == "encounter_001"
    assert encounter["roll_ids"] == [roll["id"]]


def test_legacy_dice_roll_request_links_roll_to_event(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "dice_roll_request",
                "target": {"kind": "roll"},
                "content": "旧形式の判定",
                "constraints": {"notation": "1d20", "target": 10},
                "visibility": "gm_only",
            }
        ),
    )

    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    roll = next(item for item in rolls if item["dice"] and item["dice"]["notation"] == "1d20")
    event = next(item for item in events if item["type"] == "dice_roll_request")
    assert event["roll_ids"] == [roll["id"]]


def test_character_check_persists_chance_roll_and_links_event(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")
    character_path = project_path.parent / "workspace" / "state" / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character.update({"stats": {"知力": 9}, "skills": {"観察": 6}})
    character_path.write_text(
        yaml.safe_dump(character, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "dice_roll_request",
                "target": {"kind": "character", "id": "char_001"},
                "content": "痕跡を見つけられるか",
                "constraints": {"target": 50, "stat": "知力", "skill": "観察"},
                "visibility": "gm_only",
            }
        ),
    )

    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    roll = next(item for item in rolls if item["type"] == "chance")
    event = next(item for item in events if item["type"] == "dice_roll_request")
    assert roll["chance"]["base_chance"] == 50
    assert roll["chance"]["modifiers"] == {"stat:知力": 9, "skill:観察": 6}
    assert roll["chance"]["final_chance"] == 65
    assert event["roll_ids"] == [roll["id"]]
    assert event["effects"]["character_id"] == "char_001"


def test_canon_edit_and_hidden_truth_edit_produce_state_diff_changes(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "canon_edit",
                "target": {"kind": "canon"},
                "content": "新しい確定事実",
                "visibility": "canon",
            },
            {
                "type": "hidden_truth_edit",
                "target": {"kind": "gm_vault"},
                "content": "新しい隠し真実",
                "visibility": "gm_only",
            },
        ),
    )

    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    targets = {change["target"] for change in state_diff["diff"]["changes"]}
    assert {"canon", "gm_vault"} <= targets
    assert result.status == TurnStatus.APPLIED


def test_reveal_now_promotes_gm_vault_fact_via_full_pipeline(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")
    _add_gm_vault_entry(project_path, "gm_vault_001", "隠された真実")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "reveal_control",
                "target": {"kind": "gm_vault", "id": "gm_vault_001"},
                "content": "reveal it",
                "constraints": {"mode": "reveal-now"},
                "visibility": "reader",
            }
        ),
    )

    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    reader_state_changes = [
        change for change in state_diff["diff"]["changes"] if change["target"] == "reader_state"
    ]
    assert any(change["value"]["text"] == "隠された真実" for change in reader_state_changes)
    assert result.status == TurnStatus.APPLIED


def test_event_injection_scene_transition_flips_scenes_via_full_pipeline(tmp_path, build_project):
    """Issue 009: a GM-forced event_injection carrying effects.scene_transition ends the
    current scene, activates the pending one, and carries the cast over."""
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")
    _add_pending_scene(project_path, "scene_002")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "event_injection",
                "target": {"kind": "world"},
                "content": "追跡者が姿を現す",
                "constraints": {"scene_transition": {"end": "scene_001", "start": "scene_002"}},
                "visibility": "reader",
            }
        ),
    )

    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    scene_changes = [c for c in state_diff["diff"]["changes"] if c["target"] == "scene"]
    assert {
        (c["id"], c["path"], c["value"] if not isinstance(c["value"], list) else tuple(c["value"]))
        for c in scene_changes
    } == {
        ("scene_001", "status", "ended"),
        ("scene_002", "status", "active"),
        ("scene_002", "active_characters", ("char_001",)),
    }
    assert result.status != "failed"


def test_interventions_yaml_accumulates_history_after_an_applied_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=_drafts(
            {
                "type": "world_directive",
                "target": {"kind": "world"},
                "content": "雨が降り始める",
                "visibility": "reader",
            }
        ),
    )

    history_path = project_path.parent / "workspace" / "interventions.yaml"
    history = yaml.safe_load(history_path.read_text(encoding="utf-8"))
    assert len(history["entries"]) == 1
    entry = history["entries"][0]
    assert entry["type"] == "world_directive"
    assert entry["source_event_ids"]
    assert entry["superseded_by_rerun"] is False
    assert result.status == TurnStatus.APPLIED
