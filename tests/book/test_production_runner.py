from __future__ import annotations

import yaml

from living_narrative.book.budget import BookBudgetPolicy
from living_narrative.book.coordinator import (
    apply_book_plan_proposal,
    plan_generation,
    request_chapter_revision,
    start_chapter_production,
)
from living_narrative.book.drafting import run_chapter_draft
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_runner import (
    ChapterProductionRunner,
    ProductionRunPhase,
)
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project


class _Gateway:
    def __init__(self) -> None:
        self.binding_keys: list[str] = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.binding_keys.append(binding_key)
        if binding_key == "chapter_draft":
            return response_schema(
                body="澪は駅の時刻表に刻まれた矛盾を発見し、夜明け前の改札へ向かった。"
            )
        if binding_key == "chapter_continuity":
            return response_schema(required_threads_covered=[], findings=[])
        raise AssertionError(f"unexpected binding: {binding_key}")


class _FailingDraftGateway(_Gateway):
    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.binding_keys.append(binding_key)
        if binding_key == "chapter_draft":
            raise RuntimeError("credential=top-secret path=/private/prompt.yaml")
        raise AssertionError(f"unexpected binding: {binding_key}")


class _StopBeforeReviewGateway(_Gateway):
    def __init__(self, runner, project_yaml) -> None:
        super().__init__()
        self.runner = runner
        self.project_yaml = project_yaml

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        response = super().complete(binding_key, messages, response_schema, prompt_template_name)
        if binding_key == "chapter_continuity":
            self.runner.request_stop(self.project_yaml, "chapter_001")
        return response


class _StopAfterDraftGateway(_Gateway):
    def __init__(self, runner, project_yaml) -> None:
        super().__init__()
        self.runner = runner
        self.project_yaml = project_yaml

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        response = super().complete(binding_key, messages, response_schema, prompt_template_name)
        if binding_key == "chapter_draft":
            self.runner.request_stop(self.project_yaml, "chapter_001")
        return response


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


def test_runner_moves_a_planned_chapter_to_explicit_author_review(tmp_path):
    project_yaml = _project(tmp_path)
    gateway = _Gateway()

    status = ChapterProductionRunner().run(project_yaml, "chapter_001", gateway=gateway)

    assert status.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert status.lifecycle is ChapterLifecycle.REVIEW
    assert status.draft_run_id is not None
    assert status.attempt_id == "attempt_001"
    assert gateway.binding_keys == ["chapter_draft", "chapter_continuity"]

    run_root = project_yaml.parent / "workspace" / "runs" / "chapter_production" / "chapter_001"
    manifests = list(run_root.glob("*/manifest.yaml"))
    assert len(manifests) == 1
    manifest = yaml.safe_load(manifests[0].read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["phase"] == "awaiting_author"
    assert "body" not in manifest
    assert "prompt" not in manifest
    assert (manifests[0].parent / "events" / "001_preparing.yaml").exists()
    assert (manifests[0].parent / "events" / "004_awaiting_author.yaml").exists()


def test_runner_reuses_a_persisted_draft_response_without_calling_the_draft_provider(tmp_path):
    project_yaml = _project(tmp_path)
    workspace = project_yaml.parent / "workspace"
    start_chapter_production(workspace, "chapter_001")
    initial_gateway = _Gateway()
    draft = run_chapter_draft(project_yaml, "chapter_001", gateway=initial_gateway)
    assert initial_gateway.binding_keys == ["chapter_draft"]

    resumed_gateway = _Gateway()
    status = ChapterProductionRunner().run(project_yaml, "chapter_001", gateway=resumed_gateway)

    assert status.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert status.resumed is False
    assert draft.run_id == status.draft_run_id
    assert resumed_gateway.binding_keys == ["chapter_continuity"]


def test_runner_stops_at_the_boundary_after_draft_before_recording_a_candidate(tmp_path):
    project_yaml = _project(tmp_path)
    runner = ChapterProductionRunner()
    gateway = _StopAfterDraftGateway(runner, project_yaml)

    status = runner.run(project_yaml, "chapter_001", gateway=gateway)

    assert status.phase is ProductionRunPhase.STOPPED
    assert status.lifecycle is ChapterLifecycle.RUNNING
    assert status.stopped_reason == "author_requested"
    assert gateway.binding_keys == ["chapter_draft"]
    chapters_root = project_yaml.parent / "workspace" / "books" / "chapters"
    assert not (chapters_root / "chapter_001" / "candidate.md").exists()


def test_runner_fails_closed_before_provider_call_when_manifest_and_lifecycle_conflict(tmp_path):
    project_yaml = _project(tmp_path)
    workspace = project_yaml.parent / "workspace"
    bundle = StateStore.load(workspace / "state")
    run_id = f"generation_{plan_generation(bundle)}_revision_001"
    run_dir = workspace / "runs" / "chapter_production" / "chapter_001" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "request.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "run_id": run_id, "chapter_id": "chapter_001"}),
        encoding="utf-8",
    )
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "run_id": run_id,
                "chapter_id": "chapter_001",
                "phase": "candidate_recorded",
            }
        ),
        encoding="utf-8",
    )
    gateway = _Gateway()

    try:
        ChapterProductionRunner().run(project_yaml, "chapter_001", gateway=gateway)
    except ValueError as exc:
        assert "inconsistent production run" in str(exc)
    else:
        raise AssertionError("manifest/lifecycle conflict must be rejected")

    status = ChapterProductionRunner().status(project_yaml, "chapter_001")
    assert status.phase is ProductionRunPhase.FAILED
    assert status.lifecycle is ChapterLifecycle.PLANNED
    assert gateway.binding_keys == []
    failure = yaml.safe_load((run_dir / "failure.yaml").read_text(encoding="utf-8"))
    assert failure["code"] == "valueerror"


def test_runner_resumes_from_recorded_candidate_without_calling_a_provider_again(tmp_path):
    project_yaml = _project(tmp_path)
    runner = ChapterProductionRunner()
    stopping_gateway = _StopBeforeReviewGateway(runner, project_yaml)

    stopped = runner.run(project_yaml, "chapter_001", gateway=stopping_gateway)

    assert stopped.phase is ProductionRunPhase.STOPPED
    assert stopped.lifecycle is ChapterLifecycle.CANDIDATE
    assert stopping_gateway.binding_keys == ["chapter_draft", "chapter_continuity"]

    resumed_gateway = _Gateway()
    resumed = runner.run(project_yaml, "chapter_001", gateway=resumed_gateway)

    assert resumed.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert resumed.lifecycle is ChapterLifecycle.REVIEW
    assert resumed.resumed is True
    assert resumed_gateway.binding_keys == []


def test_runner_stops_before_provider_call_when_revision_budget_is_exhausted(tmp_path):
    project_yaml = _project(tmp_path)
    runner = ChapterProductionRunner()
    runner.run(project_yaml, "chapter_001", gateway=_Gateway())
    request_chapter_revision(project_yaml.parent / "workspace", "chapter_001")
    blocked_gateway = _Gateway()

    status = runner.run(
        project_yaml,
        "chapter_001",
        gateway=blocked_gateway,
        budget=BookBudgetPolicy(max_attempts_per_chapter=1),
    )

    assert status.phase is ProductionRunPhase.STOPPED
    assert status.lifecycle is ChapterLifecycle.REVISING
    assert status.stopped_reason == "chapter attempt budget exceeded"
    assert blocked_gateway.binding_keys == []
    run_root = project_yaml.parent / "workspace" / "runs" / "chapter_production" / "chapter_001"
    manifests = list(run_root.glob("*/manifest.yaml"))
    assert len(manifests) == 2
    manifest = yaml.safe_load(max(manifests).read_text(encoding="utf-8"))
    assert manifest["phase"] == "stopped"

    resumed = runner.run(project_yaml, "chapter_001", gateway=_Gateway())

    assert resumed.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert resumed.lifecycle is ChapterLifecycle.REVIEW
    assert resumed.resumed is True


def test_runner_applies_a_pre_draft_stop_request_without_calling_a_provider(tmp_path):
    project_yaml = _project(tmp_path)
    workspace = project_yaml.parent / "workspace"
    bundle = StateStore.load(workspace / "state")
    run_id = f"generation_{plan_generation(bundle)}_revision_001"
    run_dir = workspace / "runs" / "chapter_production" / "chapter_001" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "request.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "run_id": run_id, "chapter_id": "chapter_001"}),
        encoding="utf-8",
    )
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "run_id": run_id,
                "chapter_id": "chapter_001",
                "phase": "drafting",
            }
        ),
        encoding="utf-8",
    )
    gateway = _Gateway()
    stopped = ChapterProductionRunner().request_stop(project_yaml, "chapter_001")

    status = ChapterProductionRunner().run(project_yaml, "chapter_001", gateway=gateway)

    assert stopped.stopped_reason == "author_requested"
    assert status.phase is ProductionRunPhase.STOPPED
    assert status.lifecycle is ChapterLifecycle.RUNNING
    assert gateway.binding_keys == []


def test_runner_records_a_sanitized_provider_failure_then_resumes_the_same_run(tmp_path):
    project_yaml = _project(tmp_path)
    runner = ChapterProductionRunner()

    try:
        runner.run(project_yaml, "chapter_001", gateway=_FailingDraftGateway())
    except RuntimeError as exc:
        assert "top-secret" in str(exc)
    else:
        raise AssertionError("provider failure must be propagated to the synchronous caller")

    failed = runner.status(project_yaml, "chapter_001")
    assert failed.phase is ProductionRunPhase.FAILED
    assert failed.failure_code == "runtimeerror"
    assert "top-secret" not in failed.model_dump_json()
    run_root = project_yaml.parent / "workspace" / "runs" / "chapter_production" / "chapter_001"
    failure = yaml.safe_load(next(run_root.glob("*/failure.yaml")).read_text(encoding="utf-8"))
    assert failure == {"code": "runtimeerror", "recorded_at": failure["recorded_at"]}

    recovered = runner.run(project_yaml, "chapter_001", gateway=_Gateway())

    assert recovered.phase is ProductionRunPhase.AWAITING_AUTHOR
    assert recovered.resumed is True
    assert recovered.failure_code is None


def test_runner_fails_closed_when_review_lifecycle_conflicts_with_manifest_phase(tmp_path):
    project_yaml = _project(tmp_path)
    runner = ChapterProductionRunner()
    runner.run(project_yaml, "chapter_001", gateway=_Gateway())
    run_root = project_yaml.parent / "workspace" / "runs" / "chapter_production" / "chapter_001"
    manifest_path = next(run_root.glob("*/manifest.yaml"))
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["phase"] = "candidate_recorded"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    try:
        runner.run(project_yaml, "chapter_001", gateway=_Gateway())
    except ValueError as exc:
        assert "inconsistent production run" in str(exc)
    else:
        raise AssertionError("review/manifest conflict must be rejected")

    status = runner.status(project_yaml, "chapter_001")
    assert status.phase is ProductionRunPhase.FAILED
    assert status.lifecycle is ChapterLifecycle.REVIEW
