import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus

ARTIFACT_FILES = [
    "intervention.yaml",
    "events.yaml",
    "rolls.yaml",
    "narration.md",
    "checks.yaml",
    "state_diff.yaml",
    "meta.yaml",
]


def test_mock_turn_completes_with_all_artifacts(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    for filename in ARTIFACT_FILES:
        assert (result.turn_dir / filename).exists(), filename
    assert (result.turn_dir / "agent_io").is_dir()

    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    assert len(events) >= 1
    assert events[0]["type"] == "character_action"


def test_meta_yaml_contains_required_fields(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path)
    meta = yaml.safe_load((result.turn_dir / "meta.yaml").read_text(encoding="utf-8"))

    assert meta["status"] == "applied"
    for phase in (
        "load",
        "intervene",
        "simulate",
        "act",
        "resolve",
        "narrate",
        "check",
        "commit",
    ):
        assert phase in meta["phase_durations"]
    assert isinstance(meta["llm_call_count"], int) and meta["llm_call_count"] >= 0
    assert isinstance(meta["llm_calls"], list)
    assert isinstance(meta["prompt_hashes"], list)
    assert isinstance(meta["rng_draws_consumed"], int)
    assert meta["pipeline_version"]
    if meta["llm_call_count"] > 0:
        call = meta["llm_calls"][0]
        assert call["binding_key"]
        assert call["profile_name"]
        assert call["model"]


def test_multiple_llm_profiles_recorded_individually(tmp_path, build_project):
    project_path = build_project(tmp_path)
    project_data = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project_data["llm_profiles"] = {"large": {"provider": "mock", "model": "mock-large"}}
    project_data["llm_bindings"] = {"character:char_001": "large"}
    project_path.write_text(yaml.safe_dump(project_data, allow_unicode=True), encoding="utf-8")

    result = TurnPipeline().run(project_path)
    meta = yaml.safe_load((result.turn_dir / "meta.yaml").read_text(encoding="utf-8"))

    assert len(meta["llm_calls"]) == 1
    assert meta["llm_calls"][0]["profile_name"] == "large"
    assert meta["llm_calls"][0]["model"] == "mock-large"
