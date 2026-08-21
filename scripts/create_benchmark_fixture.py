#!/usr/bin/env python3
"""Create a deterministic chapter-count benchmark project without provider calls."""

from __future__ import annotations

import argparse
from pathlib import Path

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.workspace.init import create_project


def create_fixture(output: Path, *, chapter_count: int = 9) -> Path:
    """Create a deterministic BookPlan fixture without calling a provider."""
    if output.exists():
        raise ValueError(f"benchmark fixture output already exists: {output}")
    if chapter_count <= 0:
        raise ValueError("chapter_count must be positive")
    chapters = [
        {
            "id": f"chapter_{index:03d}",
            "act_id": f"act_{(index - 1) // 3 + 1:03d}",
            "planned_goal": f"謎の第{index}の手掛かりを確認する。",
            "target_word_range": {"min_words": 100, "max_words": 200},
        }
        for index in range(1, chapter_count + 1)
    ]
    acts = [
        {
            "id": f"act_{act_index:03d}",
            "promise": f"第{act_index}幕の謎を前進させる。",
            "chapter_ids": [
                f"chapter_{chapter_index:03d}"
                for chapter_index in range(
                    (act_index - 1) * 3 + 1,
                    min(act_index * 3, chapter_count) + 1,
                )
            ],
        }
        for act_index in range(1, (chapter_count + 2) // 3 + 1)
    ]
    project_yaml = create_project(output, title=f"Benchmark {chapter_count}")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": f"失われた地図の断片を{chapter_count}章で照合する。",
                "audience": "fantasy readers",
                "language": "ja",
                "acts": acts,
                "chapters": chapters,
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New project directory")
    parser.add_argument(
        "--chapters",
        type=int,
        default=9,
        help="Deterministic positive chapter count",
    )
    args = parser.parse_args()
    print(create_fixture(args.output, chapter_count=args.chapters))


if __name__ == "__main__":
    main()
