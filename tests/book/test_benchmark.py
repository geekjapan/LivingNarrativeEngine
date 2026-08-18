from __future__ import annotations

import yaml

from living_narrative.book.benchmark import benchmark_book, write_book_benchmark_report
from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.lineage import accept_chapter_attempt, record_chapter_attempt
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.review import ChapterReview, ChapterReviewDecision, ChapterReviewMetrics
from living_narrative.workspace.init import create_project
from living_narrative.workspace.loader import load_project


def test_book_benchmark_writes_public_stable_report_without_workspace_path(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Benchmark")
    workspace = project_yaml.parent / "workspace"

    observation = benchmark_book(workspace, name="empty-book")
    report_path = write_book_benchmark_report(tmp_path / "report.json", [observation])
    report = report_path.read_text(encoding="utf-8")

    assert observation.planned_chapters == 0
    assert observation.accepted_chapters == 0
    assert len(observation.artifact_fingerprint) == 64
    assert '"schema_version": 1' in report
    assert str(workspace) not in report
    assert "prompt" not in report


def _two_chapter_workspace(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Benchmark")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "帳簿を調べる。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "調査",
                        "chapter_ids": ["chapter_001", "chapter_002"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "矛盾を見つける。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    },
                    {
                        "id": "chapter_002",
                        "act_id": "act_001",
                        "planned_goal": "記録を照合する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    },
                ],
            }
        )
    )
    workspace = project_yaml.parent / "workspace"
    apply_book_plan_proposal(workspace, proposal)
    return workspace


def _review(chapter_id: str) -> ChapterReview:
    return ChapterReview(
        chapter_id=chapter_id,
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )


def test_benchmark_fingerprint_binds_chapter_lineage_and_accepted_attempt(tmp_path):
    first_workspace = _two_chapter_workspace(tmp_path / "first")
    second_workspace = _two_chapter_workspace(tmp_path / "second")
    chapters_a = first_workspace / "books" / "chapters"
    chapters_b = second_workspace / "books" / "chapters"
    record_chapter_attempt(
        chapters_a,
        ChapterCandidate(chapter_id="chapter_001", source_turns=[1], markdown="# first\n"),
        _review("chapter_001"),
    )
    record_chapter_attempt(
        chapters_a,
        ChapterCandidate(chapter_id="chapter_002", source_turns=[2], markdown="# second\n"),
        _review("chapter_002"),
    )
    record_chapter_attempt(
        chapters_b,
        ChapterCandidate(chapter_id="chapter_001", source_turns=[1], markdown="# second\n"),
        _review("chapter_001"),
    )
    record_chapter_attempt(
        chapters_b,
        ChapterCandidate(chapter_id="chapter_002", source_turns=[2], markdown="# first\n"),
        _review("chapter_002"),
    )
    assigned = benchmark_book(first_workspace, name="assigned")
    swapped = benchmark_book(second_workspace, name="swapped")
    revised = record_chapter_attempt(
        chapters_a,
        ChapterCandidate(chapter_id="chapter_001", source_turns=[3], markdown="# revised\n"),
        _review("chapter_001"),
    )
    accept_chapter_attempt(chapters_a, "chapter_001", "attempt_001")
    accepted_first = benchmark_book(first_workspace, name="accepted-first")
    accept_chapter_attempt(chapters_a, "chapter_001", revised.id)
    accepted_revised = benchmark_book(first_workspace, name="accepted-revised")

    assert assigned.artifact_fingerprint != swapped.artifact_fingerprint
    assert accepted_first.artifact_fingerprint != accepted_revised.artifact_fingerprint
    assert assigned.attempt_count == 2
    assert accepted_revised.attempt_count == 3


def test_benchmark_honors_configured_state_path(tmp_path):
    """A configured ``workspace.state`` must be measured, not the default layout."""
    project_yaml = create_project(tmp_path / "book", title="Benchmark")
    workspace = project_yaml.parent / "workspace"
    (workspace / "state").rename(project_yaml.parent / "canon")
    config = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    config["workspace"] = {
        "root": "workspace",
        "state": "canon",
        "runs": "workspace/runs",
        "exports": "workspace/exports",
    }
    project_yaml.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    observation = benchmark_book(load_project(project_yaml).paths, name="configured")

    assert observation.planned_chapters == 0
    assert len(observation.artifact_fingerprint) == 64
