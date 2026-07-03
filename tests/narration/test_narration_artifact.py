import yaml

from living_narrative.pipeline import TurnPipeline


def _read_frontmatter(narration_md_path):
    text = narration_md_path.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body.strip()


def test_narration_frontmatter_has_turn_style_visibility(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path, renderer_style="log")

    frontmatter, body = _read_frontmatter(result.turn_dir / "narration.md")
    assert frontmatter == {"turn": 1, "style": "log", "visibility": "reader"}
    assert body


def test_project_renderer_default_is_used_when_no_override(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path)

    frontmatter, _ = _read_frontmatter(result.turn_dir / "narration.md")
    assert frontmatter["style"] == "novel"


def test_call_level_style_override_wins_over_project_default(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path, renderer_style="log")

    frontmatter, _ = _read_frontmatter(result.turn_dir / "narration.md")
    assert frontmatter["style"] == "log"
