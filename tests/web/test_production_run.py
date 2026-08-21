import pytest

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_queue import DurableProductionWorker
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


def test_background_adapter_enqueues_without_executing_and_projects_worker_completion(
    tmp_path, monkeypatch
):
    project_yaml = _project(tmp_path)
    calls: list[tuple[str, str]] = []

    def completed_run(self, project, chapter_id, *, gateway=None, budget=None):
        calls.append((str(project), chapter_id))
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
        completed_run,
    )

    started = start_chapter_production_run(project_yaml, "chapter_001")

    assert started.running is True
    assert started.status.phase is ProductionRunPhase.CREATED
    assert calls == []

    with pytest.raises(ChapterProductionRunAlreadyRunningError):
        start_chapter_production_run(project_yaml, "chapter_001")

    result = DurableProductionWorker().run_once(project_yaml, worker_id="worker-alpha")

    assert result.claimed is True
    assert calls == [(str(project_yaml), "chapter_001")]
    completed = get_chapter_production_run(project_yaml, "chapter_001")
    assert completed.running is False
    assert completed.status.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert completed.status.lifecycle is ChapterLifecycle.REVIEW


def test_background_adapter_stops_a_queued_delivery_before_any_runner_call_and_can_resume(
    tmp_path, monkeypatch
):
    project_yaml = _project(tmp_path)
    calls: list[str] = []

    def completed_run(self, project, chapter_id, *, gateway=None, budget=None):
        calls.append(chapter_id)
        return ChapterProductionRunStatus(
            run_id="generation_example_revision_001",
            chapter_id=chapter_id,
            phase=ProductionRunPhase.AWAITING_AUTHOR,
            lifecycle=ChapterLifecycle.REVIEW,
        )

    monkeypatch.setattr(
        "living_narrative.web.production_run.ChapterProductionRunner.run",
        completed_run,
    )
    from living_narrative.web.production_run import stop_chapter_production_run

    start_chapter_production_run(project_yaml, "chapter_001")
    stopped = stop_chapter_production_run(project_yaml, "chapter_001")

    assert stopped.running is False
    assert stopped.status.phase is ProductionRunPhase.STOPPED
    assert stopped.status.lifecycle is ChapterLifecycle.PLANNED
    assert calls == []

    resumed = start_chapter_production_run(project_yaml, "chapter_001")
    assert resumed.running is True
    result = DurableProductionWorker().run_once(project_yaml, worker_id="worker-alpha")

    assert result.claimed is True
    assert calls == ["chapter_001"]
