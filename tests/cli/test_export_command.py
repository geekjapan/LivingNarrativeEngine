import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
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
