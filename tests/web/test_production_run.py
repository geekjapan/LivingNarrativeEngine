from __future__ import annotations

import threading
import time

import pytest

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_runner import (
    ChapterProductionRunStatus,
    ProductionRunPhase,
)
from living_narrative.state.models import ChapterLifecycle
from living_narrative.web.production_run import (
    ChapterProductionRunAlreadyRunningError,
    get_chapter_production_run,
    start_chapter_production_run,
)
from living_narrative.workspace.init import create_project


def _project(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "霧の駅から帰還する。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "異常を知る。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "時刻表の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml


def _wait_until(predicate, *, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_background_adapter_prevents_duplicate_start_and_projects_completed_status(
    tmp_path, monkeypatch
):
    project_yaml = _project(tmp_path)
    entered = threading.Event()
    release = threading.Event()

    def delayed_run(self, project, chapter_id, *, gateway=None, budget=None):
        entered.set()
        assert release.wait(timeout=2.0)
        return ChapterProductionRunStatus(
            run_id="generation_example_revision_001",
            chapter_id=chapter_id,
            phase=ProductionRunPhase.AWAITING_AUTHOR,
            lifecycle=ChapterLifecycle.REVIEW,
            draft_run_id="chapter_chapter_001_example_attempt_001",
            attempt_id="attempt_001",
        )

    monkeypatch.setattr(
        "living_narrative.web.production_run.ChapterProductionRunner.run",
        delayed_run,
    )

    started = start_chapter_production_run(project_yaml, "chapter_001")
    assert started.running is True
    assert entered.wait(timeout=2.0)

    with pytest.raises(ChapterProductionRunAlreadyRunningError):
        start_chapter_production_run(project_yaml, "chapter_001")

    release.set()
    assert _wait_until(lambda: not get_chapter_production_run(project_yaml, "chapter_001").running)
    completed = get_chapter_production_run(project_yaml, "chapter_001")
    assert completed.running is False
    assert completed.status.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert completed.status.lifecycle is ChapterLifecycle.REVIEW
