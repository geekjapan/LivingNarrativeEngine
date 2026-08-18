from __future__ import annotations

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.book.coordinator import apply_book_plan_proposal  # noqa: E402
from living_narrative.book.planning import StoryBible, build_book_plan_proposal  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402
from living_narrative.workspace.init import create_project  # noqa: E402


def _client_with_book(tmp_path, *, user_mode: str = "author") -> TestClient:
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
    return TestClient(create_app(root))


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
    for action in ("start", "accept", "revise"):
        response = client.post(f"/api/project/book/book/chapters/chapter_001/{action}")
        assert response.status_code == 403, action
