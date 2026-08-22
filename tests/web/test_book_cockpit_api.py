from __future__ import annotations

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import living_narrative.web.app as web_app  # noqa: E402
from living_narrative.book.coordinator import apply_book_plan_proposal  # noqa: E402
from living_narrative.book.planning import StoryBible, build_book_plan_proposal  # noqa: E402
from living_narrative.book.production_admission import (  # noqa: E402
    load_project_production_admission,
)
from living_narrative.book.production_runner import (  # noqa: E402
    ChapterProductionRunStatus,
    ProductionRunPhase,
)
from living_narrative.web.app import create_app  # noqa: E402
from living_narrative.web.production_run import ProductionRunInfo  # noqa: E402
from living_narrative.workspace.init import create_project  # noqa: E402
from living_narrative.workspace.loader import load_project  # noqa: E402


def _client_with_book(
    tmp_path, *, user_mode: str = "author", return_project_yaml: bool = False
) -> TestClient | tuple[TestClient, object]:
    root = tmp_path / "projects"
    project_yaml = create_project(root / "book", title="Book")
    config = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    config["user_mode"] = user_mode
    project_yaml.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "書庫から飢饉帳簿の矛盾を調べる。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "帳簿の矛盾を発見する。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "飢饉帳簿の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    client = TestClient(create_app(root))
    return (client, project_yaml) if return_project_yaml else client


def test_book_cockpit_api_projects_safe_read_model_and_start_action(tmp_path):
    client = _client_with_book(tmp_path)

    initial = client.get("/api/project/book/book/cockpit")
    started = client.post("/api/project/book/book/chapters/chapter_001/start")
    updated = client.get("/api/project/book/book/cockpit")

    assert initial.status_code == 200
    assert initial.json()["premise"] == "書庫から飢饉帳簿の矛盾を調べる。"
    chapter = initial.json()["chapters"][0]
    assert chapter["chapter_id"] == "chapter_001"
    assert "id" not in chapter
    assert chapter["lifecycle"] == "planned"
    assert chapter["target_min_words"] == 10
    assert chapter["target_max_words"] == 100
    assert chapter["startable"] is True
    assert updated.json()["chapters"][0]["startable"] is False
    assert started.status_code == 200
    assert started.json()["lifecycle"] == "running"
    assert updated.json()["active_chapter_id"] == "chapter_001"
    assert updated.json()["chapters"][0]["lifecycle"] == "running"


def test_book_cockpit_api_projects_reader_safe_budget_and_resume_eligibility(tmp_path):
    client, project_yaml = _client_with_book(tmp_path, return_project_yaml=True)
    (project_yaml.parent / "cost_policy.yaml").write_text(
        yaml.safe_dump(
            {
                "price_snapshot": {
                    "profile_id": "provider-a/fiction",
                    "version": "2026-08-21",
                    "input_usd_per_1m": "1.50",
                    "output_usd_per_1m": "6.00",
                    "tax_rate": "0.00",
                    "discount_rate": "0.00",
                },
                "budgets": {"book": {"soft_usd": "1.00", "hard_usd": "2.00"}},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = client.get("/api/project/book/book/cockpit")

    assert response.status_code == 200
    budget = response.json()["budget"]
    assert budget == {
        "status": "allow",
        "reason": None,
        "price_version": "2026-08-21",
        "actual_usd": "0",
        "estimated_usd": None,
        "variance_usd": None,
        "forecast_usd": "0",
        "remaining_hard_usd": "2.00",
        "resume_allowed": True,
    }
    assert "prompt" not in response.text
    assert "credential" not in response.text


def test_book_cockpit_api_reuses_completed_start_operation_idempotently(tmp_path):
    client = _client_with_book(tmp_path)

    first = client.post("/api/project/book/book/chapters/chapter_001/start")
    repeated = client.post("/api/project/book/book/chapters/chapter_001/start")

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json()["journal_id"] == first.json()["journal_id"]
    assert "/" not in first.json()["journal_id"]


@pytest.mark.parametrize("user_mode", ["watcher", "assistant_gm"])
def test_book_mutations_require_an_authoring_mode(tmp_path, user_mode):
    """docs/design/long-form-cockpit-architecture.md §2: only author/full_gm/god drive
    production. Non-authoring modes still read the cockpit but every mutation is 403."""
    client = _client_with_book(tmp_path, user_mode=user_mode)

    assert client.get("/api/project/book/book/cockpit").status_code == 200
    for action in ("start", "run", "run/stop", "accept", "revise"):
        response = client.post(f"/api/project/book/book/chapters/chapter_001/{action}")
        assert response.status_code == 403, action


def test_book_mutations_follow_configured_workspace_paths(tmp_path):
    """``workspace.state``/``runs`` are configurable: the coordinator must receive the resolved
    paths, not re-derive them from the workspace root."""
    root = tmp_path / "projects"
    project_yaml = create_project(root / "book", title="Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "書庫から飢饉帳簿の矛盾を調べる。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "帳簿の矛盾を発見する。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "飢饉帳簿の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    workspace = project_yaml.parent / "workspace"
    (workspace / "state").rename(project_yaml.parent / "canon")
    (workspace / "runs").rename(project_yaml.parent / "history")
    config = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    config["user_mode"] = "author"
    config["workspace"] = {
        "root": "workspace",
        "state": "canon",
        "runs": "history",
        "exports": "workspace/exports",
    }
    project_yaml.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    apply_book_plan_proposal(load_project(project_yaml).paths, proposal)
    client = TestClient(create_app(root))

    started = client.post("/api/project/book/book/chapters/chapter_001/start")

    assert started.status_code == 200, started.text
    assert started.json()["lifecycle"] == "running"
    assert (project_yaml.parent / "history" / ".transactions").is_dir()
    assert not (workspace / "runs").exists()


def test_book_run_api_starts_background_production_with_a_reader_safe_status(tmp_path, monkeypatch):
    client = _client_with_book(tmp_path)

    def start_run(_project_yaml, chapter_id):
        return ProductionRunInfo(
            running=True,
            status=ChapterProductionRunStatus(
                run_id="generation_example_revision_001",
                chapter_id=chapter_id,
                phase=ProductionRunPhase.DRAFTING,
                lifecycle="running",
            ),
        )

    monkeypatch.setattr(web_app, "start_book_chapter_run", start_run)

    response = client.post("/api/project/book/book/chapters/chapter_001/run")

    assert response.status_code == 202
    payload = response.json()
    assert payload["running"] is True
    assert payload["status"]["phase"] == "drafting"
    assert payload["status"]["lifecycle"] == "running"
    assert "prompt" not in payload
    assert "credential" not in payload


def test_book_cockpit_page_renders_budget_projection_and_disables_blocked_start(tmp_path):
    client = _client_with_book(tmp_path)

    page = client.get("/").text

    assert 'id="book-budget"' in page
    assert "function renderBookBudget(budget)" in page
    assert "budget.resume_allowed !== false" in page
    assert "予算により停止中" in page


def test_book_run_api_blocks_when_hard_budget_cannot_be_evaluated(tmp_path):
    client, project_yaml = _client_with_book(tmp_path, return_project_yaml=True)
    (project_yaml.parent / "cost_policy.yaml").write_text(
        yaml.safe_dump(
            {"price_snapshot": None, "budgets": {"book": {"hard_usd": "2.00"}}},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = client.post("/api/project/book/book/chapters/chapter_001/run")

    assert response.status_code == 409
    assert response.json()["detail"] == "book USD budget cannot be evaluated"


def test_book_cockpit_api_projects_reader_safe_production_operations(tmp_path):
    client, project_yaml = _client_with_book(tmp_path, return_project_yaml=True)

    response = client.get("/api/project/book/book/cockpit")

    assert response.status_code == 200
    assert response.json()["operations"] == {
        "queue": {
            "total_jobs": 0,
            "queued_jobs": 0,
            "leased_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "stopped_jobs": 0,
            "retry_count": 0,
            "oldest_lease_age_seconds": None,
            "failure_code_counts": {},
            "delivery_duration_count": 0,
            "delivery_duration_total_ms": 0,
            "delivery_duration_max_ms": None,
        },
        "budget_stops": {
            "total_stops": 0,
            "reason_counts": {},
        },
    }
    assert "prompt" not in response.text
    assert "credential" not in response.text
    assert str(project_yaml) not in response.text


def test_book_cockpit_api_projects_reader_safe_admission_operations_when_configured(tmp_path):
    client, project_yaml = _client_with_book(tmp_path, return_project_yaml=True)
    (project_yaml.parent / "production_admission.yaml").write_text(
        "scheduler_root: shared-scheduler\nforecast_usd: '0.75'\n",
        encoding="utf-8",
    )
    configured = load_project_production_admission(project_yaml)
    assert configured is not None
    admitted = configured.controller.try_admit(configured.request_for(project_yaml))
    assert admitted.allowed is True

    response = client.get("/api/project/book/book/cockpit")

    assert response.status_code == 200
    admission = response.json()["operations"]["admission"]
    assert admission == {
        "active_admissions": 1,
        "reserved_usd": "0.75",
        "deferred_reason_counts": {},
        "oldest_admission_age_seconds": 0,
    }
    assert "prompt" not in response.text
    assert "credential" not in response.text
    assert str(project_yaml) not in response.text
