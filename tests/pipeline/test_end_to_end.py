import yaml

from living_narrative.narration.models import NarrationResult, ThreadUpdateCandidate
from living_narrative.pipeline import TurnPipeline, TurnStatus
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project

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


def test_narrator_scene_summary_update_is_committed_to_scene_state(
    tmp_path, build_project, monkeypatch
):
    """Issue 007: the narrator's scene_summary_update must flow through BuildDiff into the
    committed scene state (mock provider fills optional fields with their default of None, so
    the narrate phase is faked here to exercise the driver -> state_manager wiring directly).
    """
    from living_narrative.pipeline import driver as driver_module

    project_path = build_project(tmp_path)

    def fake_run_narrate_phase(*, gateway, project, context, style, mood, tone_control):
        return (
            NarrationResult(
                text="霧の奥へ歩き始めた。",
                style="novel",
                scene_summary_update="霧の奥へ歩き始めた。",
            ),
            {"mode": "llm", "style": "novel"},
        )

    monkeypatch.setattr(driver_module, "run_narrate_phase", fake_run_narrate_phase)

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    scene_changes = [c for c in state_diff["diff"]["changes"] if c["target"] == "scene"]
    assert len(scene_changes) == 1
    assert scene_changes[0]["path"] == "summary"
    assert scene_changes[0]["value"] == "霧の奥へ歩き始めた。"
    assert scene_changes[0]["visibility"] == "scene"

    read = load_project(project_path)
    bundle = StateStore.load(read.paths.state)
    assert bundle.scenes[0].summary == "霧の奥へ歩き始めた。"


def test_narrator_thread_updates_are_committed_across_a_mock_turn(
    tmp_path, build_project, monkeypatch
):
    """Issue 014: the narrator's thread_updates must flow through BuildDiff into the committed
    unresolved-thread ledger (mock provider fills optional fields with their default of empty,
    so the narrate phase is faked here, same as 007's scene-summary wiring test)."""
    from living_narrative.pipeline import driver as driver_module

    project_path = build_project(tmp_path)

    def fake_run_narrate_phase(*, gateway, project, context, style, mood, tone_control):
        return (
            NarrationResult(
                text="お守りを見つけた。",
                style="novel",
                thread_updates=[
                    ThreadUpdateCandidate(action="open", description="お守りの由来は謎のままだ。")
                ],
            ),
            {"mode": "llm", "style": "novel"},
        )

    monkeypatch.setattr(driver_module, "run_narrate_phase", fake_run_narrate_phase)

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    thread_changes = [c for c in state_diff["diff"]["changes"] if c["target"] == "threads"]
    assert len(thread_changes) == 1
    assert thread_changes[0]["value"]["description"] == "お守りの由来は謎のままだ。"
    assert thread_changes[0]["value"]["status"] == "open"

    read = load_project(project_path)
    bundle = StateStore.load(read.paths.state)
    assert len(bundle.unresolved_threads) == 1
    assert bundle.unresolved_threads[0].description == "お守りの由来は謎のままだ。"


def test_narrator_memory_summary_update_is_committed_across_a_mock_turn(
    tmp_path, build_project, monkeypatch
):
    """Issue 015: the narrator's memory_summary_update must flow through BuildDiff into the
    committed memory-summary ledger (mock provider fills optional fields with their default of
    empty, so the narrate phase is faked here, same as 007/014's wiring tests)."""
    from living_narrative.pipeline import driver as driver_module

    project_path = build_project(tmp_path, memory_summary_interval=1)

    def fake_run_narrate_phase(*, gateway, project, context, style, mood, tone_control):
        return (
            NarrationResult(
                text="お守りを見つけた。",
                style="novel",
                memory_summary_update="序盤の出来事の通史要約その1。",
            ),
            {"mode": "llm", "style": "novel"},
        )

    monkeypatch.setattr(driver_module, "run_narrate_phase", fake_run_narrate_phase)

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    memory_changes = [c for c in state_diff["diff"]["changes"] if c["target"] == "memory"]
    assert len(memory_changes) == 1
    assert memory_changes[0]["value"]["text"] == "序盤の出来事の通史要約その1。"
    assert memory_changes[0]["value"]["up_to_turn"] == 1

    read = load_project(project_path)
    bundle = StateStore.load(read.paths.state)
    assert len(bundle.memory_summaries) == 1
    assert bundle.memory_summaries[0].text == "序盤の出来事の通史要約その1。"


def test_threat_pressure_diff_is_applied_across_a_mock_turn(tmp_path, build_project):
    """Issue 008: a threats-bearing project rolls pressure forward and persists it via a
    proper world state diff, through the real Load->...->Commit pipeline."""
    project_path = build_project(
        tmp_path,
        threats=[
            {
                "id": "threat_001",
                "name": "Pursuer",
                "pressure": 0,
                "pressure_per_turn": "2d6",
                "stages": [],
            }
        ],
    )

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    world_changes = [c for c in state_diff["diff"]["changes"] if c["target"] == "world"]
    assert len(world_changes) == 1
    assert world_changes[0]["path"] == "threats.threat_001.pressure"
    assert world_changes[0]["value"] > 0

    read = load_project(project_path)
    bundle = StateStore.load(read.paths.state)
    assert bundle.world.threats[0].pressure == world_changes[0]["value"]


def test_emotion_decay_diff_is_applied_across_a_mock_turn(tmp_path, build_project):
    """Issue 010: a character above its emotions_baseline decays toward it through the real
    Load->...->Commit pipeline, via a proper character state diff."""
    project_path = build_project(
        tmp_path,
        emotions={"fear": 80},
        emotions_baseline={"fear": 30},
        emotion_decay_per_turn=5,
    )

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    emotion_changes = [
        c
        for c in state_diff["diff"]["changes"]
        if c["target"] == "character" and c["path"] == "emotions.fear"
    ]
    assert len(emotion_changes) == 1
    assert emotion_changes[0]["value"] == -5

    read = load_project(project_path)
    bundle = StateStore.load(read.paths.state)
    assert bundle.characters[0].emotions["fear"] == 75


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
