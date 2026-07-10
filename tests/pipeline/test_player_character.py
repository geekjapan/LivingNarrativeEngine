import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus


def _set_player_mode(project_path):
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.update({"user_mode": "player_character", "player_char_id": "char_001"})
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _draft(type_, *, target_id="char_001", content="行動する", constraints=None):
    return {
        "type": type_,
        "target": {"kind": "character", "id": target_id},
        "content": content,
        "constraints": constraints or {},
        "visibility": "character",
    }


def test_bound_pc_without_input_is_not_llm_generated(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)

    result = TurnPipeline().run(project_path)

    candidates = yaml.safe_load(
        (result.turn_dir / "agent_io" / "act_candidates.yaml").read_text(encoding="utf-8")
    )
    assert not [item for item in candidates if item["character_id"] == "char_001"]


def test_pc_inventory_use_reuses_existing_state_diff_path(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)
    character_path = project_path.parent / "workspace/state/characters/char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["inventory"] = [{"id": "item_001", "name": "薬", "qty": 2}]
    character_path.write_text(yaml.safe_dump(character, allow_unicode=True), encoding="utf-8")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[
            _draft(
                "character_directive",
                content="薬を使う",
                constraints={"inventory_action": "use", "item_id": "item_001", "qty": 1},
            )
        ],
    )

    diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    inventory_changes = [
        item for item in diff["diff"]["changes"] if item.get("path") == "inventory.item_001.qty"
    ]
    assert inventory_changes[0]["op"] == "set"
    assert inventory_changes[0]["value"] == 1


def test_pc_character_check_uses_existing_roll_path(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)
    character_path = project_path.parent / "workspace/state/characters/char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character.update({"stats": {"知力": 5}, "skills": {"観察": 4}})
    character_path.write_text(yaml.safe_dump(character, allow_unicode=True), encoding="utf-8")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[
            _draft(
                "dice_roll_request",
                content="痕跡を探す",
                constraints={"target": 50, "stat": "知力", "skill": "観察"},
            )
        ],
    )

    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    assert any(item["type"] == "chance" for item in rolls)


def test_other_character_target_is_rejected_and_not_acted(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[_draft("character_directive", target_id="char_999")],
    )

    intervention = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    assert intervention["interventions"] == []
    assert intervention["rejections"][0]["target"]["id"] == "char_999"


def test_pc_check_cannot_smuggle_another_character_id(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[
            _draft(
                "dice_roll_request",
                constraints={
                    "character_id": "char_999",
                    "target": 50,
                    "stat": "知力",
                },
            )
        ],
    )

    intervention = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    assert intervention["interventions"] == []
    assert "constraints.character_id" in intervention["rejections"][0]["reason"]
    assert not any(item["type"] == "chance" for item in rolls)


def test_pc_action_and_check_outside_active_scene_are_audited_and_not_run(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)
    scene_path = project_path.parent / "workspace/state/scenes/scene_001.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["active_characters"] = []
    scene_path.write_text(yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8")

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[
            _draft("character_directive", content="場面外から行動する"),
            _draft(
                "dice_roll_request",
                content="場面外から判定する",
                constraints={"target": 50, "stat": "知力"},
            ),
        ],
    )
    intervention = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    rolls = yaml.safe_load((result.turn_dir / "rolls.yaml").read_text(encoding="utf-8"))
    candidates = yaml.safe_load(
        (result.turn_dir / "agent_io/act_candidates.yaml").read_text(encoding="utf-8")
    )
    assert intervention["interventions"] == []
    assert len(intervention["rejections"]) == 2
    assert all("not in the active scene" in item["reason"] for item in intervention["rejections"])
    assert not [item for item in candidates if item["character_id"] == "char_001"]
    assert not any(item["type"] == "chance" for item in rolls)


def test_dead_pc_action_becomes_existing_stop_condition(tmp_path, build_project):
    project_path = build_project(tmp_path, character_status="dead")
    _set_player_mode(project_path)

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[_draft("character_directive", content="立ち上がる")],
    )

    intervention = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    assert intervention["interventions"][0]["type"] == "stop_condition"
    assert intervention["rejections"][0]["type"] == "character_directive"
    assert intervention["rejections"][0]["target"] == {
        "kind": "character",
        "id": "char_001",
    }
    assert "dead" in intervention["rejections"][0]["reason"]
    assert result.status is TurnStatus.STOPPED_FOR_REVIEW


def test_explicit_stop_is_accepted_when_bound_pc_is_missing(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_player_mode(project_path)
    character_path = project_path.parent / "workspace/state/characters/char_001.yaml"
    character_path.unlink()

    result = TurnPipeline().run(
        project_path,
        intervention_drafts=[
            {
                "type": "stop_condition",
                "target": {"kind": "world"},
                "content": "ここで停止する",
                "constraints": {},
                "visibility": "character",
            }
        ],
    )

    intervention = yaml.safe_load(
        (result.turn_dir / "intervention.yaml").read_text(encoding="utf-8")
    )
    assert [item["type"] for item in intervention["interventions"]] == ["stop_condition"]
    assert intervention["rejections"] == []
    assert result.status is TurnStatus.STOPPED_FOR_REVIEW
