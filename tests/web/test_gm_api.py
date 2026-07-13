"""GM-pane API tests (docs/issues/024): read-only omniscient views over the existing web layer.

Skips entirely when the optional ``web`` extra (fastapi/uvicorn) is not installed — the core
suite must not depend on it. Uses the mock LLM provider + ``mist_station`` template (see
``tests/smoke/test_mist_station_20_turns.py``) since it ships characters with non-empty
``secrets``/``private_mind``, a multi-stage threat track, and hidden scene facts — exactly the
data this issue's endpoints are meant to surface (and the non-GM endpoints must keep hiding).
"""

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from living_narrative.pipeline import TurnPipeline  # noqa: E402
from living_narrative.web.app import create_app  # noqa: E402
from living_narrative.workspace.init import create_project  # noqa: E402

CHAR_002_SECRET = "幼い頃の記憶"
CHAR_002_PRIVATE_MIND = "あの日見たものの正体を、まだリナに話せていない"
SCENE_001_HIDDEN_FACT = "足音の主は、封印施設を探る追跡者である。"


def _client(root):
    return TestClient(create_app(root))


def _build_mist_station(tmp_path):
    return create_project(tmp_path / "mist_station", title="霧の駅", template="mist_station")


def _load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)


def _disclosure_values(project_path):
    state_dir = project_path.parent / "workspace" / "state"
    disclosed = set(_string_values(_load_yaml(state_dir / "reader_state.yaml")))
    values = []
    for entry in _load_yaml(state_dir / "gm_vault.yaml") or []:
        values.extend(_string_values(entry.get("text")))
        values.extend(_string_values(entry.get("reveal_condition")))
    for scene_path in (state_dir / "scenes").glob("*.yaml"):
        scene = _load_yaml(scene_path) or {}
        values.extend(_string_values([fact.get("text") for fact in scene.get("hidden_facts", [])]))
    for character_path in (state_dir / "characters").glob("*.yaml"):
        character = _load_yaml(character_path) or {}
        values.extend(_string_values(character.get("secrets", [])))
        values.extend(_string_values(character.get("private_mind", [])))
    return [value for value in values if value.strip() and value not in disclosed]


def _set_mode(project_path, mode):
    project = _load_yaml(project_path)
    project["user_mode"] = mode
    if mode == "player_character":
        project["player_char_id"] = "char_001"
    else:
        project.pop("player_char_id", None)
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


@pytest.mark.parametrize("mode", ["watcher", "author", "player_character"])
def test_non_gm_modes_reject_all_gm_views(tmp_path, mode):
    project_path = _build_mist_station(tmp_path)
    _set_mode(project_path, mode)

    client = _client(tmp_path)
    for suffix in ("characters", "world", "timeline", "threads", "turn/1"):
        assert client.get(f"/api/project/mist_station/gm/{suffix}").status_code == 403


def test_full_gm_mode_can_access_gm_views(tmp_path):
    project_path = _build_mist_station(tmp_path)
    _set_mode(project_path, "full_gm")

    assert _client(tmp_path).get("/api/project/mist_station/gm/characters").status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/api/project/mist_station/settings/project.yaml", {}),
        ("get", "/api/project/mist_station/settings/pricing.yaml", {}),
        ("put", "/api/project/mist_station/settings/project.yaml", {"json": {"yaml": "{}"}}),
        ("put", "/api/project/mist_station/settings/pricing.yaml", {"json": {"yaml": "{}"}}),
        ("get", "/api/project/mist_station/review", {}),
        ("post", "/api/project/mist_station/review", {"json": {"decision": "accept_all"}}),
        ("get", "/api/project/mist_station/interventions", {}),
        ("get", "/api/project/mist_station/gm/characters", {}),
        ("get", "/api/project/mist_station/gm/world", {}),
        ("get", "/api/project/mist_station/gm/timeline", {}),
        ("get", "/api/project/mist_station/gm/threads", {}),
        ("get", "/api/project/mist_station/gm/turn/1", {}),
    ],
)
def test_player_character_mode_rejects_all_sensitive_and_gm_routes(tmp_path, method, path, kwargs):
    project_path = _build_mist_station(tmp_path)
    _set_mode(project_path, "player_character")

    client = _client(tmp_path)
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403, f"{method.upper()} {path} was not denied"


# --- gm/characters --------------------------------------------------------------------


def test_gm_characters_returns_full_visibility_fields(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/characters")

    assert response.status_code == 200
    characters = response.json()
    assert {c["id"] for c in characters} == {"char_001", "char_002", "char_003", "char_004"}

    char_002 = next(c for c in characters if c["id"] == "char_002")
    assert char_002["secrets"] == [CHAR_002_SECRET]
    assert char_002["private_mind"] == [CHAR_002_PRIVATE_MIND]
    assert char_002["emotions"] == {"fear": 40, "unease": 50}
    assert char_002["emotions_baseline"] == {"fear": 40, "unease": 50}
    assert char_002["goals"]["short_term"] == ["リナを守る"]
    assert char_002["knowledge"]["knows"] == ["この駅の奥に何かがある"]
    assert char_002["speech"]["first_person"] == "俺"
    assert char_002["status"] == "alive"


def test_gm_characters_relationships_are_from_side_only(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/characters")

    char_001 = next(c for c in response.json() if c["id"] == "char_001")
    rel_targets = {(rel["from"], rel["to"]) for rel in char_001["relationships"]}
    # char_001 (リナ) has outgoing relationships to char_002 and char_003 in the template;
    # char_004 -> char_001 must NOT appear (that's char_004's outgoing side, not char_001's).
    assert rel_targets == {("char_001", "char_002"), ("char_001", "char_003")}


def test_gm_characters_include_stats_and_skills_from_character_model(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/characters")

    assert response.status_code == 200
    char_003 = next(c for c in response.json() if c["id"] == "char_003")
    assert char_003["stats"] == {"体力": 5, "知力": 8, "意志": 8}
    assert char_003["skills"] == {"観察": 8, "封印術": 9, "隠密": 7}


def test_gm_characters_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/gm/characters")

    assert response.status_code == 404


# --- gm/world --------------------------------------------------------------------------


def test_gm_world_returns_summary_pacing_and_scenes(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/world")

    assert response.status_code == 200
    data = response.json()
    assert data["world"]["name"] == "霧の駅"
    assert data["world"]["parameters"]["danger_level"] == 55
    assert data["pacing"] == {"stall_window": 3, "pressure_boost": 4}

    scene_001 = next(s for s in data["scenes"] if s["id"] == "scene_001")
    assert scene_001["status"] == "active"
    assert scene_001["location"] == "霧の駅・地下ホーム"
    assert any(f["text"] == SCENE_001_HIDDEN_FACT for f in scene_001["hidden_facts"])
    assert scene_001["reader_visible_facts"]


def test_gm_world_threat_next_stage_is_lowest_uncrossed(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/world")

    threat = next(t for t in response.json()["threats"] if t["id"] == "threat_001")
    assert threat["pressure"] == 0
    assert len(threat["stages"]) == 4
    assert threat["next_stage"]["at"] == 25  # the lowest stage not yet crossed at pressure 0


def test_gm_world_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/gm/world")

    assert response.status_code == 404


# --- gm/threads --------------------------------------------------------------------------


def test_gm_threads_includes_notes_opened_turn_and_related_event_count(tmp_path):
    project_path = _build_mist_station(tmp_path)
    state_dir = project_path.parent / "workspace" / "state"
    (state_dir / "unresolved_threads.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "thread_001",
                    "description": "足音の正体",
                    "status": "open",
                    "related_event_ids": ["event_0001", "event_0002"],
                    "notes": ["まだ解決していない"],
                    "opened_turn": 1,
                }
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (state_dir / "memory_summaries.yaml").write_text(
        yaml.safe_dump(
            [{"id": "memory_0001", "up_to_turn": 1, "text": "駅で足音が響いた。"}],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    response = _client(tmp_path).get("/api/project/mist_station/gm/threads")

    assert response.status_code == 200
    data = response.json()
    assert len(data["threads"]) == 1
    thread = data["threads"][0]
    assert thread["notes"] == ["まだ解決していない"]
    assert thread["opened_turn"] == 1
    assert thread["related_event_count"] == 2
    assert data["memory_summaries"][0]["text"] == "駅で足音が響いた。"


def test_gm_threads_empty_when_none_recorded(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/threads")

    assert response.status_code == 200
    assert response.json() == {"threads": [], "memory_summaries": []}


def test_gm_threads_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/gm/threads")

    assert response.status_code == 404


# --- gm/timeline -----------------------------------------------------------------------


def test_gm_timeline_hydrates_events_with_visibility(tmp_path):
    project_path = _build_mist_station(tmp_path)
    TurnPipeline().run(project_path)
    TurnPipeline().run(project_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/timeline")

    assert response.status_code == 200
    entries = response.json()
    assert [e["turn"] for e in entries] == [1, 2]
    for entry in entries:
        assert entry["events"], f"turn {entry['turn']} should have hydrated events"
        for event in entry["events"]:
            assert "visibility" in event
            assert event["turn"] == entry["turn"]


def test_gm_timeline_from_query_skips_earlier_turns(tmp_path):
    project_path = _build_mist_station(tmp_path)
    TurnPipeline().run(project_path)
    TurnPipeline().run(project_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/timeline?from=2")

    entries = response.json()
    assert [e["turn"] for e in entries] == [2]


def test_gm_timeline_limit_caps_entries(tmp_path):
    project_path = _build_mist_station(tmp_path)
    TurnPipeline().run(project_path)
    TurnPipeline().run(project_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/timeline?limit=1")

    entries = response.json()
    assert [e["turn"] for e in entries] == [1]


def test_gm_timeline_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/gm/timeline")

    assert response.status_code == 404


# --- gm/turn/{n} -----------------------------------------------------------------------


def test_gm_turn_detail_returns_rolls_checks_state_diff(tmp_path):
    project_path = _build_mist_station(tmp_path)
    TurnPipeline().run(project_path)
    turn_dir = project_path.parent / "workspace" / "runs" / "turn_0001"

    response = _client(tmp_path).get("/api/project/mist_station/gm/turn/1")

    assert response.status_code == 200
    data = response.json()
    assert data["turn"] == 1
    assert data["rolls"] == _load_yaml(turn_dir / "rolls.yaml")
    assert data["checks"] == _load_yaml(turn_dir / "checks.yaml")
    assert data["state_diff"] == _load_yaml(turn_dir / "state_diff.yaml")


def test_gm_turn_detail_404_on_missing_turn(tmp_path):
    _build_mist_station(tmp_path)

    response = _client(tmp_path).get("/api/project/mist_station/gm/turn/999")

    assert response.status_code == 404


def test_gm_turn_detail_unknown_project_is_404(tmp_path):
    response = _client(tmp_path).get("/api/project/does-not-exist/gm/turn/1")

    assert response.status_code == 404


# --- regression: non-GM endpoints must keep the leak boundary intact -------------------


def test_non_gm_endpoints_never_leak_secrets_private_mind_or_hidden_facts(tmp_path):
    project_path = _build_mist_station(tmp_path)
    TurnPipeline().run(project_path)
    client = _client(tmp_path)

    # These are the reader-facing state GET APIs; the root HTML shell intentionally contains
    # hidden GM-pane templates, while mutation responses contain only control metadata.
    endpoints = (
        ("projects", client.get("/api/projects")),
        ("status", client.get("/api/project/mist_station/status")),
        ("narration", client.get("/api/project/mist_station/narration")),
        ("turns", client.get("/api/project/mist_station/turns")),
        ("run_status", client.get("/api/project/mist_station/run_status")),
        ("permissions", client.get("/api/project/mist_station/permissions")),
    )
    forbidden_markers = ("gm_vault", "hidden_facts", "secrets", "private_mind")
    forbidden_values = _disclosure_values(project_path)
    for label, response in endpoints:
        assert response.status_code == 200, f"{label} failed: {response.text}"
        for marker in forbidden_markers:
            assert marker not in response.text, f"{label} leaked disclosure marker {marker!r}"
        response_values = list(_string_values(response.json()))
        for value in forbidden_values:
            assert all(value not in item for item in response_values), (
                f"{label} leaked GM-only content: {value!r}"
            )
