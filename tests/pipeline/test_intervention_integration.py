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
    non_timeline_changes = [c for c in state_diff["diff"]["changes"] if c["target"] != "timeline"]
    assert non_timeline_changes == []


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
