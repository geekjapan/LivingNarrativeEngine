import json

import yaml

from living_narrative.narration.llm_narrator import LLMNarratorOutput
from living_narrative.narration.models import NarrationResult, ThreadUpdateCandidate
from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.state.models import Event, Visibility
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project
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


def test_overdue_narrator_thread_origin_flows_from_history_to_committed_diff(
    tmp_path, build_project, monkeypatch
):
    project_path = build_project(tmp_path)
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project["llm_profiles"] = {"prose": {"provider": "mock", "model": "mock-prose"}}
    project["llm_bindings"] = {"narrator": "prose"}
    project_path.write_text(yaml.safe_dump(project, allow_unicode=True), encoding="utf-8")
    state_dir = project_path.parent / "workspace" / "state"
    state_dir.joinpath("unresolved_threads.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "thread_000101",
                    "description": "語り手が開いた糸",
                    "status": "open",
                    "related_event_ids": [],
                    "notes": [],
                    "opened_turn": 1,
                },
                {
                    "id": "thread_000102",
                    "description": "作者が開いた糸",
                    "status": "open",
                    "related_event_ids": [],
                    "notes": [],
                    "opened_turn": 1,
                },
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    state_dir.joinpath("timeline.yaml").write_text(
        yaml.safe_dump(
            [{"turn": 1, "event_ids": ["event_0001", "event_0002"]}],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    runs_dir = project_path.parent / "workspace" / "runs"
    turn_1 = runs_dir / "turn_0001"
    turn_1.mkdir(parents=True)
    turn_1.joinpath("events.yaml").write_text(
        yaml.safe_dump(
            [
                Event(
                    id="event_0001",
                    turn=1,
                    type="thread_update",
                    cause="narrator",
                    text="語り手が開いた糸",
                    visibility=Visibility.GM_ONLY,
                    effects={"action": "open", "thread_id": "thread_000101"},
                ).model_dump(mode="json"),
                Event(
                    id="event_0002",
                    turn=1,
                    type="thread_update",
                    cause="authored:affordance_001",
                    text="作者が開いた糸",
                    visibility=Visibility.READER,
                    effects={"action": "open", "thread_id": "thread_000102"},
                ).model_dump(mode="json"),
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    turn_25 = runs_dir / "turn_0025"
    turn_25.mkdir()
    turn_25.joinpath("meta.yaml").write_text("turn: 25\nstatus: applied\n", encoding="utf-8")

    payloads = []

    def fake_complete(self, binding_key, messages, response_schema, prompt_template_name):
        payloads.append(json.loads(messages[1]["content"]))
        return LLMNarratorOutput(prose="足音は霧の中へ続いていた。")

    monkeypatch.setattr("living_narrative.pipeline.llm_gateway.LLMGateway.complete", fake_complete)
    registry = default_registry()
    registry.register("simulate", lambda context, interventions: [])
    registry.register(
        "act",
        lambda context, world_events, gateway, interventions=(), past_events=None: ([], []),
    )
    registry.register(
        "resolve",
        lambda context, world_events, action_candidates, allocate_event_id, record_roll: [
            Event(
                id=allocate_event_id(),
                turn=context.turn,
                type="background_event",
                text="足音は霧の中へ続いている",
                visibility=Visibility.READER,
            )
        ],
    )

    result = TurnPipeline(registry=registry).run(project_path)

    assert result.status == TurnStatus.APPLIED
    assert payloads[0]["open_threads"] == [
        {
            "id": "thread_000101",
            "description": "語り手が開いた糸",
            "turns_open": 25,
            "origin": "narrator",
        },
        {
            "id": "thread_000102",
            "description": "作者が開いた糸",
            "turns_open": 25,
            "origin": "authored",
        },
    ]
    state_diff = yaml.safe_load((result.turn_dir / "state_diff.yaml").read_text(encoding="utf-8"))
    thread_changes = [
        change for change in state_diff["diff"]["changes"] if change["target"] == "threads"
    ]
    assert [(change["id"], change["value"]) for change in thread_changes] == [
        ("thread_000101", "resolved")
    ]
    bundle = StateStore.load(state_dir)
    assert [(thread.id, thread.status) for thread in bundle.unresolved_threads] == [
        ("thread_000101", "resolved"),
        ("thread_000102", "open"),
    ]


def test_mist_station_fallback_outcome_reaches_grounded_narration_once(tmp_path, monkeypatch):
    project_path = create_project(
        tmp_path / "mist_station", title="霧の駅", template="mist_station"
    )
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project["llm_profiles"] = {"prose": {"provider": "mock", "model": "mock-prose"}}
    project["llm_bindings"] = {"narrator": "prose"}
    project_path.write_text(yaml.safe_dump(project, allow_unicode=True), encoding="utf-8")
    state_dir = project_path.parent / "workspace" / "state"
    state_dir.joinpath("timeline.yaml").write_text(
        yaml.safe_dump(
            [{"turn": turn, "event_ids": [f"event_{turn:04d}"]} for turn in range(1, 4)],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    runs_dir = project_path.parent / "workspace" / "runs"
    for turn in range(1, 4):
        turn_dir = runs_dir / f"turn_{turn:04d}"
        turn_dir.mkdir(parents=True)
        turn_dir.joinpath("events.yaml").write_text(
            yaml.safe_dump(
                [
                    Event(
                        id=f"event_{turn:04d}",
                        turn=turn,
                        type="background_event",
                        text=f"{turn}ターン目の静かな霧",
                        visibility=Visibility.READER,
                    ).model_dump(mode="json")
                ],
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    runs_dir.joinpath("turn_0003", "meta.yaml").write_text(
        "turn: 3\nstatus: applied\n", encoding="utf-8"
    )

    payloads = []

    def fake_complete(self, binding_key, messages, response_schema, prompt_template_name):
        payload = json.loads(messages[1]["content"])
        payloads.append(payload)
        outcome = next(
            event["text"]
            for event in payload["reader_visible_events"]
            if event["type"] == "action_outcome"
        )
        return LLMNarratorOutput(prose=f"{outcome}。")

    monkeypatch.setattr("living_narrative.pipeline.llm_gateway.LLMGateway.complete", fake_complete)
    registry = default_registry()
    registry.register("simulate", lambda context, interventions: [])
    registry.register(
        "act",
        lambda context, world_events, gateway, interventions=(), past_events=None: ([], []),
    )

    result = TurnPipeline(registry=registry).run(project_path)

    assert result.status == TurnStatus.STOPPED_FOR_REVIEW
    fallback_text = "階段へ進み、足音の正体を確かめる"
    assert payloads[0]["reader_visible_events"] == [
        {"type": "action_outcome", "text": fallback_text}
    ]
    assert fallback_text in (result.turn_dir / "narration.md").read_text(encoding="utf-8")
    events = yaml.safe_load((result.turn_dir / "events.yaml").read_text(encoding="utf-8"))
    assert [event["type"] for event in events if event["text"] == fallback_text] == [
        "character_action",
        "action_outcome",
    ]


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
