from __future__ import annotations

import yaml
from typer.testing import CliRunner

from living_narrative.cli import app

runner = CliRunner()


def _story_bible() -> dict[str, object]:
    return {
        "premise": "霧の駅からの帰還を描く。",
        "audience": "長編ミステリ読者",
        "language": "ja",
        "acts": [
            {
                "id": "act_001",
                "promise": "閉じ込められた理由を提示する。",
                "chapter_ids": ["chapter_001"],
            }
        ],
        "chapters": [
            {
                "id": "chapter_001",
                "act_id": "act_001",
                "planned_goal": "時刻表の矛盾を発見する。",
                "required_thread_ids": ["thread_001"],
                "character_arc_targets": [],
                "target_word_range": {"min_words": 2500, "max_words": 4500},
            }
        ],
    }


def test_book_plan_writes_reviewable_structured_proposal(tmp_path):
    bible_path = tmp_path / "story-bible.yaml"
    output_path = tmp_path / "book-plan-proposal.yaml"
    bible_path.write_text(yaml.safe_dump(_story_bible(), allow_unicode=True), encoding="utf-8")

    result = runner.invoke(
        app,
        ["book", "plan", "--story-bible", str(bible_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0, result.output
    proposal = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert proposal["proposal_id"].startswith("book_plan_")
    assert proposal["book_plan"]["chapters"][0]["id"] == "chapter_001"
    assert proposal["book_ledger"]["active_chapter_id"] == "chapter_001"
    assert "canonical state was not changed" in result.output


def test_book_plan_rejects_invalid_story_bible(tmp_path):
    bible_path = tmp_path / "invalid-story-bible.yaml"
    bible_path.write_text("premise: ''\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["book", "plan", "--story-bible", str(bible_path), "--output", str(tmp_path / "out.yaml")],
    )

    assert result.exit_code == 2
    assert "story bible" in result.output
