import json

import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.pipeline import TurnPipeline

runner = CliRunner()


def _set_player_mode(project_path):
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.update({"user_mode": "player_character", "player_char_id": "char_001"})
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def test_status_human_readable_before_any_turn(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["status", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "ターン: 0" in result.output
    assert "user_mode: assistant_gm" in result.output
    assert "autonomy_level: manual" in result.output
    assert "gm_vault" not in result.output.lower()


def test_status_json_has_required_keys(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    for key in ("current_turn", "pending_review", "user_mode", "autonomy_level"):
        assert key in data
    assert data["current_turn"] == 1
    assert data["pending_review"] is False


def test_status_never_leaks_gm_vault_or_secrets(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        hidden_facts=[
            {"id": "fact_001", "text": "a deep secret", "visibility": "gm_only", "known_by": []}
        ],
    )

    result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    assert "a deep secret" not in result.output


def test_status_character_sheet_is_available_in_human_and_json_output(tmp_path, build_project):
    project_path = build_project(tmp_path)
    character_path = project_path.parent / "workspace" / "state" / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["stats"] = {"力": 6}
    character["skills"] = {"観察": 7}
    character_path.write_text(
        yaml.safe_dump(character, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    human_result = runner.invoke(app, ["status", "--project", str(project_path)])
    json_result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])

    assert human_result.exit_code == 0, human_result.output
    assert "char_001 Aoi [alive] stats={'力': 6} skills={'観察': 7}" in human_result.output
    data = json.loads(json_result.output)
    assert data["characters"] == [
        {
            "id": "char_001",
            "name": "Aoi",
            "status": "alive",
            "stats": {"力": 6},
            "skills": {"観察": 7},
        }
    ]
    serialized = json.dumps(data["characters"], ensure_ascii=False)
    assert "secrets" not in serialized
    assert "private_mind" not in serialized


def test_status_exits_2_for_missing_project(tmp_path):
    result = runner.invoke(
        app, ["status", "--project", str(tmp_path / "does_not_exist" / "project.yaml")]
    )

    assert result.exit_code == 2


def test_status_displays_llm_usage_and_unknown_price(tmp_path, build_project):
    project_path = build_project(tmp_path)
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "llm_tokens_total": 12,
                "llm_calls": [
                    {
                        "provider_name": "test",
                        "model": "auto/best-coding",
                        "duration_seconds": 0.1,
                        "prompt_template_name": "test",
                        "prompt_hash": "hash",
                        "prompt_tokens": 5,
                        "completion_tokens": 7,
                        "total_tokens": 12,
                        "profile_name": "main",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["status", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    assert "LLM利用: 1 calls / 12 tokens" in result.output
    assert "概算費用: 価格未設定" in result.output
    assert "model auto/best-coding: 1 calls / 12 tokens / 価格未設定" in result.output
    assert "profile main: 1 calls / 12 tokens / 価格未設定" in result.output

    json_result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])
    usage = json.loads(json_result.output)["llm_usage"]
    assert usage["by_model"][0]["model"] == "auto/best-coding"
    assert usage["by_profile"][0]["profile_name"] == "main"


def test_player_status_omits_does_not_know_and_out_of_scene_scene_facts(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        reader_visible_facts=["読者には見える"],
        hidden_facts=[
            {
                "id": "fact_001",
                "text": "現場にいる者だけ",
                "visibility": "scene",
                "known_by": [],
            },
            {
                "id": "fact_002",
                "text": "本人が知っている",
                "visibility": "character",
                "known_by": ["char_001"],
            },
        ],
        knowledge={
            "knows": ["既知"],
            "believes": ["推測"],
            "does_not_know": ["秘密の正体"],
        },
        secrets=["本人の秘密"],
    )
    _set_player_mode(project_path)
    scene_path = project_path.parent / "workspace/state/scenes/scene_001.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["active_characters"] = []
    scene_path.write_text(yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8")

    result = runner.invoke(app, ["status", "--project", str(project_path), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["characters"][0]["knowledge"] == {"knows": ["既知"], "believes": ["推測"]}
    assert data["characters"][0]["secrets"] == ["本人の秘密"]
    assert data["scene"] is None
    assert data["visible_facts"] == []
    assert "秘密の正体" not in result.output
    assert "現場にいる者だけ" not in result.output
    assert "読者には見える" not in result.output
    assert "本人が知っている" not in result.output
