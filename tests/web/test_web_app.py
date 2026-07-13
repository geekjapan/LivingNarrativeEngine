"""FastAPI web layer tests (docs/issues/020). Skips entirely when the optional ``web`` extra
(fastapi/uvicorn) is not installed — the core suite must not depend on it."""

import re

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.pipeline import TurnPipeline  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402


def _client(root):
    return TestClient(create_app(root))


def test_list_projects_scans_root(tmp_path, build_project):
    build_project(tmp_path, title="My Project")

    response = _client(tmp_path).get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert data == [{"name": "project", "title": "My Project"}]


def test_list_projects_empty_root(tmp_path):
    (tmp_path / "not_a_project").mkdir()

    response = _client(tmp_path).get("/api/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_status_before_any_turn(tmp_path, build_project):
    build_project(tmp_path)

    response = _client(tmp_path).get("/api/project/project/status")

    assert response.status_code == 200
    data = response.json()
    assert data["current_turn"] == 0
    assert data["pending_review"] is False
    assert data["scene"]["location"] == "駅"
    assert data["characters"] == [{"id": "char_001", "name": "Aoi", "status": "alive"}]


def test_status_never_leaks_gm_vault_or_secrets(tmp_path, build_project):
    build_project(
        tmp_path,
        hidden_facts=[
            {"id": "fact_001", "text": "a deep secret", "visibility": "gm_only", "known_by": []}
        ],
    )

    response = _client(tmp_path).get("/api/project/project/status")

    assert response.status_code == 200
    assert "a deep secret" not in response.text
    assert "secrets" not in response.json()["characters"][0]
    assert "private_mind" not in response.json()["characters"][0]


def test_player_status_uses_safe_own_character_projection(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        knowledge={
            "knows": ["既知"],
            "believes": ["推測"],
            "does_not_know": ["未知の秘密"],
        },
        secrets=["本人の秘密"],
    )
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.update({"user_mode": "player_character", "player_char_id": "char_001"})
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    response = _client(tmp_path).get("/api/project/project/status")

    assert response.status_code == 200
    character = response.json()["characters"][0]
    assert character["knowledge"] == {"knows": ["既知"], "believes": ["推測"]}
    assert character["secrets"] == ["本人の秘密"]
    assert "未知の秘密" not in response.text


def test_player_status_hides_active_scene_when_player_is_not_participant(tmp_path, build_project):
    project_path = build_project(tmp_path, reader_visible_facts=["場面の公開情報"])
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.update({"user_mode": "player_character", "player_char_id": "char_001"})
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    scene_path = project_path.parent / "workspace/state/scenes/scene_001.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["active_characters"] = []
    scene_path.write_text(yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8")

    response = _client(tmp_path).get("/api/project/project/status")

    assert response.status_code == 200
    assert response.json()["scene"] is None
    assert response.json()["visible_facts"] == []
    assert "場面の公開情報" not in response.text


def test_status_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/status")

    assert response.status_code == 404


def test_status_api_and_gm_pane_include_shared_llm_usage(tmp_path, build_project):
    project_path = build_project(tmp_path)
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "llm_tokens_total": 12,
                "llm_calls": [
                    {
                        "provider_name": "test",
                        "model": "model-exact",
                        "duration_seconds": 0.1,
                        "prompt_template_name": "test",
                        "prompt_hash": "hash",
                        "prompt_tokens": 5,
                        "completion_tokens": 7,
                        "total_tokens": 12,
                        "profile_name": "main",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    usage = client.get("/api/project/project/status").json()["llm_usage"]

    assert usage["calls"] == 1
    assert usage["total_tokens"] == 12
    assert usage["cost_usd"] is None
    assert usage["by_model"][0]["model"] == "model-exact"
    page = client.get("/").text
    assert "LLM利用量・概算費用" in page
    assert "価格未設定" in page


def test_gm_cost_pane_escapes_hostile_model_and_profile_names(tmp_path, build_project):
    project_path = build_project(tmp_path)
    hostile = '<img src=x onerror="alert(1)">'
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "llm_calls": [
                    {
                        "provider_name": "test",
                        "model": hostile,
                        "duration_seconds": 0.1,
                        "prompt_template_name": "test",
                        "prompt_hash": "hash",
                        "profile_name": hostile,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    usage = client.get("/api/project/project/status").json()["llm_usage"]
    page = client.get("/").text

    assert usage["by_model"][0]["model"] == hostile
    assert usage["by_profile"][0]["profile_name"] == hostile
    assert "${escapeHtml(m.model)}" in page
    assert '${escapeHtml(p.profile_name || "未設定")}' in page
    assert "${m.model}" not in page
    assert '${p.profile_name || "未設定"}' not in page


def test_gm_character_pane_renders_stats_and_skills_with_escaped_keys(tmp_path, build_project):
    build_project(tmp_path)

    page = _client(tmp_path).get("/").text

    assert "const stats = renderSheet(c.stats);" in page
    assert "const skills = renderSheet(c.skills);" in page
    assert "`${escapeHtml(name)}: ${escapeHtml(value)}`" in page
    assert "<div>stats: ${stats}</div>" in page
    assert "<div>skills: ${skills}</div>" in page


def test_status_character_name_and_status_are_html_escaped(tmp_path, build_project):
    build_project(tmp_path)

    page = _client(tmp_path).get("/").text

    assert "${escapeHtml(c.name)} [${escapeHtml(c.status)}]" in page
    assert "${c.name} [${c.status}]" not in page


def test_gm_character_pane_renders_one_escaped_visual_profile_line(tmp_path, build_project):
    project_yaml = build_project(tmp_path)
    character_path = project_yaml.parent / "workspace" / "state" / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["visual_profile"] = {"summary": '<img src=x onerror="alert(1)">'}
    character_path.write_text(
        yaml.safe_dump(character, allow_unicode=True),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    response = client.get("/api/project/project/gm/characters")
    page = client.get("/").text

    assert response.json()[0]["visual_profile"]["summary"] == '<img src=x onerror="alert(1)">'
    assert "escapeHtml(c.visual_profile.summary)" in page
    assert "<div>visual: ${visualProfile}</div>" in page


def test_inner_html_template_values_use_escape_html(tmp_path, build_project):
    build_project(tmp_path)
    page = _client(tmp_path).get("/").text

    function_ranges = (
        ("function renderInterventionEntry", "function renderInterventionHistory"),
        ("function renderInterventionHistory", "function visibilityBadge"),
        ("function renderReview", "async function loadReview"),
        ("function renderGmCharacters", "function renderGmLlmUsage"),
        ("function renderGmLlmUsage", "function renderGmWorld"),
        ("function renderGmWorld", "function renderGmThreads"),
        ("function renderGmThreads", "function renderGmTimeline"),
        ("function renderGmTimeline", "function renderGmTurnDetail"),
        ("function renderGmTurnDetail", "async function loadGm"),
    )
    sink_blocks = [page[page.index(start) : page.index(end)] for start, end in function_ranges]
    refresh = page[page.index("async function refresh") : page.index("async function poll")]
    sink_blocks.append(refresh[refresh.index("charactersEl.innerHTML") :])
    expressions = [
        expression.strip()
        for block in sink_blocks
        for expression in re.findall(r"\$\{(?:[^{}]|\{[^{}]*\})*\}", block)
    ]
    allowed_html_fragments = {
        "badge",
        "baselineNote",
        "body",
        "detail",
        "events",
        "emotions",
        "hidden",
        "models",
        "next",
        "privateMind",
        "profiles",
        "relationships",
        "secrets",
        "skills",
        "stats",
        "summaries",
        "threads",
        "threats",
        "visualProfile",
    }
    unsafe = [
        expression
        for expression in expressions
        if not expression.startswith("${escapeHtml(")
        and not expression.startswith("${statusBadge(")
        and not expression.startswith("${visibilityBadge(")
        and not expression.startswith("${severityBadge(")
        and expression[2:-1].strip() not in allowed_html_fragments
    ]

    assert unsafe == []


def test_hostile_project_payload_stays_in_json_and_is_escaped_in_page(tmp_path, build_project):
    hostile = '<img src=x onerror="alert(1)">'
    project_path = build_project(tmp_path, scene_summary=hostile)
    world_path = project_path.parent / "workspace" / "state" / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    world["summary"] = hostile
    world_path.write_text(yaml.safe_dump(world, allow_unicode=True), encoding="utf-8")

    client = _client(tmp_path)
    response = client.get("/api/project/project/gm/world")
    page = client.get("/").text

    assert response.json()["world"]["summary"] == hostile
    assert response.json()["scenes"][0]["summary"] == hostile
    assert "escapeHtml(world.world.summary)" in page
    assert 'escapeHtml(s.summary || "")' in page


@pytest.mark.parametrize("name", ["..", "../etc", "a/b", "a\\b", ""])
def test_path_traversal_rejected(tmp_path, build_project, name):
    build_project(tmp_path)

    response = _client(tmp_path).get(f"/api/project/{name}/status")

    assert response.status_code == 404


def test_path_traversal_cannot_escape_root_via_symlink(tmp_path, build_project):
    outside = tmp_path.parent / "outside_secret"
    outside.mkdir(exist_ok=True)
    (outside / "project.yaml").write_text("id: outside\n", encoding="utf-8")
    root = tmp_path / "served_root"
    root.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)

    response = _client(root).get("/api/project/escape/status")

    assert response.status_code == 404


def test_turn_and_narration_round_trip(tmp_path, build_project):
    project_path = build_project(tmp_path)

    client = _client(tmp_path)
    turn_response = client.post("/api/project/project/turn")

    assert turn_response.status_code == 200
    turn_data = turn_response.json()
    assert turn_data["turn"] == 1
    assert turn_data["status"] in {"applied", "pending_review", "stopped_for_review", "failed"}

    status_response = client.get("/api/project/project/status")
    assert status_response.json()["current_turn"] == 1 or turn_data["status"] != "applied"

    narration_response = client.get("/api/project/project/narration")
    assert narration_response.status_code == 200
    assert narration_response.headers["content-type"].startswith("text/plain")

    # sanity: narration matches what TurnPipeline itself wrote for this project
    del project_path


def test_narration_never_leaks_hidden_facts(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        hidden_facts=[
            {"id": "fact_001", "text": "a deep secret", "visibility": "gm_only", "known_by": []}
        ],
    )
    TurnPipeline().run(project_path)

    response = _client(tmp_path).get("/api/project/project/narration")

    assert response.status_code == 200
    assert "a deep secret" not in response.text


def test_narration_from_query_skips_earlier_turns(tmp_path, build_project):
    project_path = build_project(tmp_path)
    TurnPipeline().run(project_path)
    TurnPipeline().run(project_path)

    client = _client(tmp_path)
    full = client.get("/api/project/project/narration").text
    from_turn_2 = client.get("/api/project/project/narration?from=2").text

    assert from_turn_2 != full
    assert len(from_turn_2) < len(full)


def test_narration_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/narration")

    assert response.status_code == 404


def test_index_serves_html(tmp_path):
    response = _client(tmp_path).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text
