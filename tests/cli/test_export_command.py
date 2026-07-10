import importlib

import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.export_replay import VNLineOutput, VNTurnOutput
from living_narrative.llm.errors import StructuredOutputError
from living_narrative.pipeline import TurnPipeline

runner = CliRunner()


def _set_user_mode(project_path, user_mode: str) -> None:
    data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    data["user_mode"] = user_mode
    project_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_export_replay_writes_output_and_creates_parent_dirs(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    output = tmp_path / "out" / "replay.md"

    result = runner.invoke(
        app,
        [
            "export",
            "replay",
            "--project",
            str(project_path),
            "--output",
            str(output),
            "--style",
            "novel",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()


def test_export_replay_errors_when_no_turns_have_run(tmp_path, build_project):
    project_path = build_project(tmp_path)
    output = tmp_path / "replay.md"

    result = runner.invoke(
        app, ["export", "replay", "--project", str(project_path), "--output", str(output)]
    )

    assert result.exit_code == 1
    assert not output.exists()


def test_export_replay_rejects_unknown_style(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    output = tmp_path / "replay.md"

    result = runner.invoke(
        app,
        [
            "export",
            "replay",
            "--project",
            str(project_path),
            "--output",
            str(output),
            "--style",
            "unknown_style",
        ],
    )

    assert result.exit_code == 2


def test_export_scenes_writes_yaml_and_markdown_under_workspace_exports(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "scenes", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    assert (exports_dir / "scenes.yaml").exists()
    assert (exports_dir / "scenes.md").exists()


def test_export_scenes_accepts_gm_flag(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "scenes", "--project", str(project_path), "--gm"])

    assert result.exit_code == 0, result.output


def test_export_vn_script_formats_normal_novel_narration_with_profile(
    tmp_path, build_project, monkeypatch
):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    character_path = state_dir / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["visual_profile"] = {"summary": "黒髪"}
    character_path.write_text(yaml.safe_dump(character, allow_unicode=True), encoding="utf-8")
    (state_dir / "visual_profiles.yaml").write_text(
        yaml.safe_dump(
            {"backgrounds": [{"id": "background_001", "name": "駅", "summary": "夜の駅"}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    TurnPipeline().run(project_path)
    calls = []

    class Gateway:
        def __init__(self, **kwargs):
            pass

        def complete(self, binding_key, messages, response_schema, prompt_template_name):
            calls.append(binding_key)
            return VNTurnOutput(
                lines=[
                    VNLineOutput(
                        type="dialogue",
                        speaker="char_001",
                        text="行こう",
                        sprite="char_001",
                        background="background_001",
                    ),
                    VNLineOutput(type="narration", text="霧が晴れる"),
                    VNLineOutput(type="direction", text="暗転"),
                ]
            )

    export_cli = importlib.import_module("living_narrative.cli.export")
    monkeypatch.setattr(export_cli, "LLMGateway", Gateway)

    result = runner.invoke(
        app,
        [
            "export",
            "vn-script",
            "--project",
            str(project_path),
            "--profile",
            "vn-editor",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == ["vn-editor"]
    exports_dir = project_path.parent / "workspace" / "exports"
    script = yaml.safe_load((exports_dir / "script.yaml").read_text(encoding="utf-8"))
    kinds = [command["kind"] for command in script["turns"][0]["commands"]]
    assert kinds == ["background", "sprite", "dialogue", "narration", "direction"]
    assert "**char_001**: 行こう" in (exports_dir / "script.md").read_text(encoding="utf-8")


def test_export_vn_script_reports_exhausted_structured_output(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    class FailingGateway:
        def __init__(self, **kwargs):
            pass

        def complete(self, *args, **kwargs):
            raise StructuredOutputError(
                provider_name="mock",
                model="m",
                schema_name="VNTurnOutput",
                last_error="retry exhausted",
            )

    export_cli = importlib.import_module("living_narrative.cli.export")
    monkeypatch.setattr(export_cli, "LLMGateway", FailingGateway)

    result = runner.invoke(app, ["export", "vn-script", "--project", str(project_path)])

    assert result.exit_code == 1
    assert "VN script LLM formatting failed for turn 1" in result.output
    assert not (project_path.parent / "workspace" / "exports" / "script.yaml").exists()


def test_export_tts_script_reads_canonical_vn_script(tmp_path, build_project):
    project_path = build_project(tmp_path)
    workspace = project_path.parent / "workspace"
    (workspace / "state" / "voice_profiles.yaml").write_text(
        "characters:\n"
        "  - character_id: char_001\n    quality: 明るい声\n"
        "narrator:\n  quality: 静かな語り\n",
        encoding="utf-8",
    )
    (workspace / "exports").mkdir(parents=True, exist_ok=True)
    (workspace / "exports" / "script.yaml").write_text(
        "format: living-narrative-vn-script-v1\n"
        "warnings: []\n"
        "turns:\n"
        "  - turn: 1\n"
        "    commands:\n"
        "      - kind: background\n        text: 秘密の背景\n"
        "      - kind: dialogue\n        character_id: char_001\n        text: 行こう\n"
        "      - kind: narration\n        text: 霧が晴れる\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["export", "tts-script", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    data = yaml.safe_load((workspace / "exports" / "tts_script.yaml").read_text(encoding="utf-8"))
    assert [segment["text"] for segment in data["segments"]] == ["行こう", "霧が晴れる"]
    assert "秘密の背景" not in (workspace / "exports" / "tts_script.md").read_text(encoding="utf-8")


def test_export_tts_script_rejects_malformed_canonical_input(tmp_path, build_project):
    project_path = build_project(tmp_path)
    exports = project_path.parent / "workspace" / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "script.yaml").write_text("turns: not-a-list\n", encoding="utf-8")

    result = runner.invoke(app, ["export", "tts-script", "--project", str(project_path)])

    assert result.exit_code == 1
    assert "invalid canonical VN script schema" in result.output
    assert not (exports / "tts_script.yaml").exists()


def test_export_help_lists_image_and_tts_provider_subcommands():
    result = runner.invoke(app, ["export", "--help"])

    assert result.exit_code == 0, result.output
    assert "images" in result.output
    assert "tts-script" in result.output


def test_export_image_prompts_writes_yaml_and_markdown_with_profile(tmp_path, build_project):
    project_path = build_project(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    character_path = state_dir / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["visual_profile"] = {"summary": "short black hair", "hair": "black"}
    character_path.write_text(yaml.safe_dump(character, allow_unicode=True), encoding="utf-8")
    (state_dir / "visual_profiles.yaml").write_text(
        yaml.safe_dump(
            {
                "backgrounds": [{"id": "background_001", "name": "駅", "summary": "night station"}],
                "style_lock": {"art_style": "anime background art"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    TurnPipeline().run(project_path)

    result = runner.invoke(
        app,
        ["export", "image-prompts", "--project", str(project_path), "--profile", "narrator"],
    )

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    assert (exports_dir / "image_prompts.yaml").exists()
    assert (exports_dir / "image_prompts.md").exists()


def test_export_image_prompts_errors_without_visual_profiles(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "image-prompts", "--project", str(project_path)])

    assert result.exit_code == 1
    exports_dir = project_path.parent / "workspace" / "exports"
    assert not (exports_dir / "image_prompts.yaml").exists()


def test_export_images_generates_cached_manifest_and_updates_status(tmp_path, build_project):
    project_path = build_project(tmp_path)
    exports_dir = project_path.parent / "workspace" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    (exports_dir / "image_prompts.yaml").write_text(
        yaml.safe_dump(
            {
                "notice": "生成画像の権利・利用条件はproviderに依存します。",
                "prompts": [
                    {
                        "scene_id": "scene_001",
                        "japanese_description": "夜の駅",
                        "english_prompt": "A quiet station at night",
                        "character_appearance_lock": [],
                        "background_lock": {},
                        "style_lock": {},
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    first = runner.invoke(
        app,
        [
            "export",
            "images",
            "--project",
            str(project_path),
            "--provider",
            "mock",
            "--profile",
            "draft",
        ],
    )
    second = runner.invoke(
        app,
        ["export", "images", "--project", str(project_path), "--profile", "draft"],
    )

    assert first.exit_code == second.exit_code == 0
    manifest_path = exports_dir / "assets" / "assets.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["assets"]) == 1
    asset = manifest["assets"][0]
    assert asset["rights_notice"]
    assert (exports_dir / "assets" / asset["path"]).exists()

    accepted = runner.invoke(
        app,
        ["export", "images", "--project", str(project_path), "--accept", asset["id"]],
    )
    assert accepted.exit_code == 0, accepted.output
    updated = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert updated["assets"][0]["status"] == "accepted"


def test_export_images_rejects_unknown_asset_conflicting_actions_and_provider(
    tmp_path, build_project
):
    project_path = build_project(tmp_path)

    conflict = runner.invoke(
        app,
        [
            "export",
            "images",
            "--project",
            str(project_path),
            "--accept",
            "asset_0123456789abcdef0123456789abcdef",
            "--discard",
            "asset_0123456789abcdef0123456789abcdef",
        ],
    )
    unknown = runner.invoke(
        app,
        [
            "export",
            "images",
            "--project",
            str(project_path),
            "--accept",
            "asset_0123456789abcdef0123456789abcdef",
        ],
    )

    assert conflict.exit_code == 2
    assert unknown.exit_code == 1
    assert "unknown asset" in unknown.output


def test_export_images_rejects_symlink_assets_directory_without_external_write(
    tmp_path, build_project
):
    project_path = build_project(tmp_path)
    exports_dir = project_path.parent / "workspace" / "exports"
    (exports_dir / "image_prompts.yaml").write_text(
        yaml.safe_dump(
            {
                "notice": "生成画像の権利・利用条件はproviderに依存します。",
                "prompts": [
                    {
                        "scene_id": "scene_001",
                        "japanese_description": "夜の駅",
                        "english_prompt": "A quiet station at night",
                        "character_appearance_lock": [],
                        "background_lock": {},
                        "style_lock": {},
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    outside = tmp_path / "outside-assets"
    outside.mkdir()
    (exports_dir / "assets").symlink_to(outside, target_is_directory=True)

    result = runner.invoke(app, ["export", "images", "--project", str(project_path)])

    assert result.exit_code == 1
    assert "must not be a symlink" in result.output
    assert list(outside.iterdir()) == []


def test_export_images_rejects_symlink_manifest_without_external_write(tmp_path, build_project):
    project_path = build_project(tmp_path)
    assets_dir = project_path.parent / "workspace" / "exports" / "assets"
    assets_dir.mkdir()
    outside_manifest = tmp_path / "outside-assets.yaml"
    original = b"rights_notice: outside\nassets: []\n"
    outside_manifest.write_bytes(original)
    (assets_dir / "assets.yaml").symlink_to(outside_manifest)

    result = runner.invoke(
        app,
        [
            "export",
            "images",
            "--project",
            str(project_path),
            "--accept",
            "asset_0123456789abcdef0123456789abcdef",
        ],
    )

    assert result.exit_code == 1
    assert "manifest must not be a symlink" in result.output
    assert outside_manifest.read_bytes() == original
    assert not (assets_dir / "files").exists()


def test_export_scenes_errors_when_project_not_found(tmp_path):
    output = tmp_path / "does_not_exist" / "project.yaml"

    result = runner.invoke(app, ["export", "scenes", "--project", str(output)])

    assert result.exit_code == 2


def test_export_outline_writes_yaml_and_markdown_under_workspace_exports(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "outline", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    assert (exports_dir / "outline.yaml").exists()
    assert (exports_dir / "outline.md").exists()
    assert "# 章立て" in (exports_dir / "outline.md").read_text(encoding="utf-8")


def test_export_outline_errors_when_no_turns_have_run(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["export", "outline", "--project", str(project_path)])

    assert result.exit_code == 1
    exports_dir = project_path.parent / "workspace" / "exports"
    assert not (exports_dir / "outline.yaml").exists()


def test_export_outline_errors_when_project_not_found(tmp_path):
    output = tmp_path / "does_not_exist" / "project.yaml"

    result = runner.invoke(app, ["export", "outline", "--project", str(output)])

    assert result.exit_code == 2


def test_export_novel_writes_novel_draft_under_workspace_exports(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "novel", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    novel_path = project_path.parent / "workspace" / "exports" / "novel_draft.md"
    assert novel_path.exists()
    content = novel_path.read_text(encoding="utf-8")
    assert "第1章" in content


def test_export_novel_accepts_profile_flag(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(
        app, ["export", "novel", "--project", str(project_path), "--profile", "narrator"]
    )

    assert result.exit_code == 0, result.output


def test_export_novel_errors_when_no_turns_have_run(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["export", "novel", "--project", str(project_path)])

    assert result.exit_code == 1
    novel_path = project_path.parent / "workspace" / "exports" / "novel_draft.md"
    assert not novel_path.exists()


def test_export_novel_errors_when_project_not_found(tmp_path):
    output = tmp_path / "does_not_exist" / "project.yaml"

    result = runner.invoke(app, ["export", "novel", "--project", str(output)])

    assert result.exit_code == 2


def test_export_replay_trpg_includes_rolls_interventions_and_scene_heading(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _set_user_mode(project_path, "full_gm")
    TurnPipeline().run(
        project_path,
        intervention_drafts=[
            {
                "type": "world_directive",
                "target": {"kind": "world"},
                "content": "雨が降り始める",
                "visibility": "reader",
            },
            {
                "type": "dice_roll_request",
                "target": {"kind": "roll"},
                "content": "気づくかどうか",
                "constraints": {"notation": "2d6", "target": 7},
                "visibility": "gm_only",
            },
        ],
    )
    output = tmp_path / "trpg_replay.md"

    result = runner.invoke(
        app,
        [
            "export",
            "replay",
            "--project",
            str(project_path),
            "--output",
            str(output),
            "--trpg",
        ],
    )

    assert result.exit_code == 0, result.output
    content = output.read_text(encoding="utf-8")
    assert "GM出力" in content
    assert "ロール欄" in content
    assert "2d6" in content
    assert "介入欄" in content
    assert "GM介入: world_directive — 雨が降り始める" in content
    assert "シーン: 駅" in content


def test_export_replay_trpg_errors_when_no_turns_have_run(tmp_path, build_project):
    project_path = build_project(tmp_path)
    output = tmp_path / "trpg_replay.md"

    result = runner.invoke(
        app,
        ["export", "replay", "--project", str(project_path), "--output", str(output), "--trpg"],
    )

    assert result.exit_code == 1
    assert not output.exists()


def test_export_replay_default_output_is_unaffected_by_trpg_feature(tmp_path, build_project):
    """Regression: the default (no --trpg) replay output must stay exactly as it was before
    Issue 028 introduced the GM-facing --trpg rendering path."""
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    output = tmp_path / "replay.md"

    result = runner.invoke(
        app, ["export", "replay", "--project", str(project_path), "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    content = output.read_text(encoding="utf-8")
    assert "GM出力" not in content
    assert "GM介入" not in content
    assert "ロール欄" not in content
    assert "介入欄" not in content


def test_export_arcs_writes_yaml_and_markdown_under_workspace_exports(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "arcs", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    assert (exports_dir / "arcs.yaml").exists()
    assert (exports_dir / "arcs.md").exists()
    content = (exports_dir / "arcs.md").read_text(encoding="utf-8")
    assert "キャラクターアーク・伏線レポート" in content


def test_export_arcs_handles_empty_project_with_zero_turns(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = runner.invoke(app, ["export", "arcs", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    content = (exports_dir / "arcs.md").read_text(encoding="utf-8")
    assert "(なし)" in content


def test_export_arcs_errors_when_project_not_found(tmp_path):
    output = tmp_path / "does_not_exist" / "project.yaml"

    result = runner.invoke(app, ["export", "arcs", "--project", str(output)])

    assert result.exit_code == 2


def test_export_revise_writes_revised_novel_and_notes_yaml(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    runner.invoke(app, ["export", "novel", "--project", str(project_path)])

    result = runner.invoke(app, ["export", "revise", "--project", str(project_path)])

    assert result.exit_code == 0, result.output
    exports_dir = project_path.parent / "workspace" / "exports"
    revised_path = exports_dir / "novel_revised.md"
    notes_path = exports_dir / "revision_notes.yaml"
    assert revised_path.exists()
    assert notes_path.exists()
    assert "第1章" in revised_path.read_text(encoding="utf-8")
    notes = yaml.safe_load(notes_path.read_text(encoding="utf-8"))
    assert set(notes.keys()) == {"repeated_phrases", "style_issues", "continuity_notes"}


def test_export_revise_accepts_profile_flag(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    runner.invoke(app, ["export", "novel", "--project", str(project_path)])

    result = runner.invoke(
        app, ["export", "revise", "--project", str(project_path), "--profile", "narrator"]
    )

    assert result.exit_code == 0, result.output


def test_export_revise_accepts_explicit_input_path(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    custom_input = tmp_path / "custom_draft.md"
    custom_input.write_text(
        "# タイトル\n\n## 第1章: 章タイトル\n\n本文がここに入る。\n", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        ["export", "revise", "--project", str(project_path), "--input", str(custom_input)],
    )

    assert result.exit_code == 0, result.output
    revised_path = project_path.parent / "workspace" / "exports" / "novel_revised.md"
    assert revised_path.exists()


def test_export_revise_errors_when_input_draft_is_missing(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)

    result = runner.invoke(app, ["export", "revise", "--project", str(project_path)])

    assert result.exit_code == 1
    exports_dir = project_path.parent / "workspace" / "exports"
    assert not (exports_dir / "novel_revised.md").exists()


def test_export_revise_errors_when_project_not_found(tmp_path):
    output = tmp_path / "does_not_exist" / "project.yaml"

    result = runner.invoke(app, ["export", "revise", "--project", str(output)])

    assert result.exit_code == 2
