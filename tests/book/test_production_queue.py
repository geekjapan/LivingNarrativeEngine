from __future__ import annotations

from living_narrative.book.coordinator import apply_book_plan_proposal
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_queue import (
    DurableProductionQueue,
    DurableProductionWorker,
    QueueJobState,
)
from living_narrative.book.production_runner import (
    ChapterProductionRunStatus,
    ProductionRunPhase,
)
from living_narrative.state.models import ChapterLifecycle
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


def test_queue_enqueues_idempotently_and_worker_completes_reader_safe_status(tmp_path, monkeypatch):
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
        "living_narrative.book.production_queue.ChapterProductionRunner.run",
        completed_run,
    )
    queue = DurableProductionQueue()

    first = queue.enqueue(project_yaml, "chapter_001")
    second = queue.enqueue(project_yaml, "chapter_001")

    assert first.job_id == second.job_id
    assert first.state is QueueJobState.QUEUED

    result = DurableProductionWorker(queue).run_once(project_yaml, worker_id="worker-alpha")

    assert result.claimed is True
    assert result.status is not None
    assert result.status.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert calls == [(str(project_yaml), "chapter_001")]

    status = queue.status(project_yaml, "chapter_001")
    assert status.state is QueueJobState.COMPLETED
    assert status.run_id == "generation_example_revision_001"
    assert status.status is not None
    assert status.status.model_dump(exclude_none=True) == {
        "run_id": "generation_example_revision_001",
        "chapter_id": "chapter_001",
        "phase": "awaiting_author",
        "lifecycle": "review",
        "draft_run_id": "chapter_chapter_001_example_attempt_001",
        "attempt_id": "attempt_001",
        "resumed": False,
    }


def test_queue_reenqueues_a_failed_delivery_with_the_same_job_id_for_safe_runner_resume(
    tmp_path, monkeypatch
):
    project_yaml = _project(tmp_path)
    calls = 0

    def timeout_then_resume(self, project, chapter_id, *, gateway=None, budget=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("provider timeout")
        return ChapterProductionRunStatus(
            run_id="generation_example_revision_001",
            chapter_id=chapter_id,
            phase=ProductionRunPhase.AWAITING_AUTHOR,
            lifecycle=ChapterLifecycle.REVIEW,
            draft_run_id="chapter_chapter_001_example_attempt_001",
            attempt_id="attempt_001",
        )

    monkeypatch.setattr(
        "living_narrative.book.production_queue.ChapterProductionRunner.run",
        timeout_then_resume,
    )
    queue = DurableProductionQueue()
    worker = DurableProductionWorker(queue)
    initial = queue.enqueue(project_yaml, "chapter_001")

    import pytest

    with pytest.raises(TimeoutError):
        worker.run_once(project_yaml, worker_id="worker-alpha")

    failed = queue.status(project_yaml, "chapter_001")
    assert failed.state is QueueJobState.FAILED
    assert failed.failure_code == "timeouterror"

    retried = queue.enqueue(project_yaml, "chapter_001")
    assert retried.job_id == initial.job_id
    assert retried.state is QueueJobState.QUEUED

    recovered = worker.run_once(project_yaml, worker_id="worker-beta")

    assert recovered.claimed is True
    assert recovered.status is not None
    assert recovered.status.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert calls == 2
    assert queue.status(project_yaml, "chapter_001").delivery_count == 2


def test_renewed_lease_blocks_redelivery_until_expiry_and_job_lock_release(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    project_yaml = _project(tmp_path)
    current = datetime(2026, 8, 21, 5, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "living_narrative.book.production_queue._utc_now",
        lambda: current,
    )
    queue = DurableProductionQueue(lease_seconds=10)
    queue.enqueue(project_yaml, "chapter_001")
    first = queue.claim(project_yaml, "worker-alpha")
    assert first is not None

    current += timedelta(seconds=9)
    queue.heartbeat(project_yaml, first)
    queue.release(first)

    current += timedelta(seconds=2)
    assert queue.claim(project_yaml, "worker-beta") is None

    current += timedelta(seconds=9)
    second = queue.claim(project_yaml, "worker-beta")
    assert second is not None
    assert second.job_id == first.job_id
    assert second.lease_generation == first.lease_generation + 1
    queue.release(second)


def test_worker_renews_its_lease_while_the_runner_is_executing(tmp_path, monkeypatch):
    import threading
    import time

    project_yaml = _project(tmp_path)
    queue = DurableProductionQueue(lease_seconds=10)
    queue.enqueue(project_yaml, "chapter_001")
    entered = threading.Event()
    release = threading.Event()
    heartbeats: list[str] = []
    original_heartbeat = queue.heartbeat

    def tracking_heartbeat(project, claim):
        heartbeats.append(claim.job_id)
        return original_heartbeat(project, claim)

    def blocking_run(self, project, chapter_id, *, gateway=None, budget=None):
        entered.set()
        assert release.wait(timeout=2.0)
        return ChapterProductionRunStatus(
            run_id="generation_example_revision_001",
            chapter_id=chapter_id,
            phase=ProductionRunPhase.AWAITING_AUTHOR,
            lifecycle=ChapterLifecycle.REVIEW,
        )

    monkeypatch.setattr(queue, "heartbeat", tracking_heartbeat)
    monkeypatch.setattr(
        "living_narrative.book.production_queue.ChapterProductionRunner.run",
        blocking_run,
    )
    worker = DurableProductionWorker(queue, heartbeat_interval_seconds=0.01)
    results = []
    thread = threading.Thread(
        target=lambda: results.append(worker.run_once(project_yaml, worker_id="worker-alpha")),
        daemon=True,
    )

    thread.start()
    assert entered.wait(timeout=2.0)
    deadline = time.monotonic() + 1.0
    while not heartbeats and time.monotonic() < deadline:
        time.sleep(0.01)
    assert heartbeats

    release.set()
    thread.join(timeout=2.0)
    assert not thread.is_alive()
    assert results[0].claimed is True
    assert queue.status(project_yaml, "chapter_001").state is QueueJobState.COMPLETED


def test_queue_allows_only_one_leased_delivery_per_book(tmp_path):
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
                        "chapter_ids": ["chapter_001", "chapter_002"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "時刻表の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    },
                    {
                        "id": "chapter_002",
                        "act_id": "act_001",
                        "planned_goal": "駅員の証言を集める。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    },
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    queue = DurableProductionQueue()
    queue.enqueue(project_yaml, "chapter_001")
    queue.enqueue(project_yaml, "chapter_002")

    first = queue.claim(project_yaml, "worker-alpha")

    assert first is not None
    assert queue.claim(project_yaml, "worker-beta") is None

    queue.complete(
        project_yaml,
        first,
        ChapterProductionRunStatus(
            run_id="generation_example_revision_001",
            chapter_id="chapter_001",
            phase=ProductionRunPhase.AWAITING_AUTHOR,
            lifecycle=ChapterLifecycle.REVIEW,
        ),
    )
    queue.release(first)

    second = queue.claim(project_yaml, "worker-beta")
    assert second is not None
    assert queue.job_for_claim(project_yaml, second) == "chapter_002"
    queue.release(second)


def test_queue_collects_reader_safe_operational_metrics(tmp_path):
    project_yaml = _project(tmp_path)
    queue = DurableProductionQueue()
    queue.enqueue(project_yaml, "chapter_001")

    from living_narrative.book.production_queue import collect_production_queue_metrics

    metrics = collect_production_queue_metrics(project_yaml)

    assert metrics.total_jobs == 1
    assert metrics.queued_jobs == 1
    assert metrics.leased_jobs == 0
    assert metrics.failed_jobs == 0
    assert metrics.retry_count == 0
    rendered = metrics.model_dump_json()
    assert str(project_yaml) not in rendered
    assert "prompt" not in rendered


def test_queue_metrics_reports_oldest_active_lease_age_without_worker_identity(tmp_path):
    project_yaml = _project(tmp_path)
    queue = DurableProductionQueue()
    queue.enqueue(project_yaml, "chapter_001")
    claim = queue.claim(project_yaml, "worker-alpha")
    assert claim is not None

    from living_narrative.book.production_queue import collect_production_queue_metrics

    metrics = collect_production_queue_metrics(project_yaml)

    assert metrics.leased_jobs == 1
    assert metrics.oldest_lease_age_seconds is not None
    assert metrics.oldest_lease_age_seconds >= 0
    assert "worker-alpha" not in metrics.model_dump_json()
    queue.release(claim)
