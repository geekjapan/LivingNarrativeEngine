#!/usr/bin/env python3
"""Create the deterministic nine-chapter project used by benchmark CI."""

from __future__ import annotations

import argparse
from pathlib import Path

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.workspace.init import create_project


def create_fixture(output: Path) -> Path:
    """Create a nine-chapter BookPlan fixture without calling a provider."""
    if output.exists():
        raise ValueError(f"benchmark fixture output already exists: {output}")
    chapters = [
        {
            "id": f"chapter_{index:03d}",
            "act_id": f"act_{(index - 1) // 3 + 1:03d}",
            "planned_goal": f"謎の第{index}の手掛かりを確認する。",
            "target_word_range": {"min_words": 100, "max_words": 200},
        }
        for index in range(1, 10)
    ]
    acts = [
        {
            "id": f"act_{act_index:03d}",
            "promise": f"第{act_index}幕の謎を前進させる。",
            "chapter_ids": [
                f"chapter_{chapter_index:03d}"
                for chapter_index in range((act_index - 1) * 3 + 1, act_index * 3 + 1)
            ],
        }
        for act_index in range(1, 4)
    ]
    project_yaml = create_project(output, title="Benchmark Nine")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "失われた地図の断片を九つの章で照合する。",
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
    args = parser.parse_args()
    print(create_fixture(args.output))


if __name__ == "__main__":
    main()
