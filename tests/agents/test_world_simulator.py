from pathlib import Path

import pytest
from pydantic import ValidationError

from living_narrative.agents.models import BackgroundEventCandidate
from living_narrative.agents.world_simulator import simulate_world
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import (
    BackgroundEventTableEntry,
    CharacterState,
    FactionState,
    LLMConfig,
    PacingConfig,
    ProjectConfig,
    ThreatStage,
    ThreatTrack,
    TimelineEntry,
    Visibility,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)
from living_narrative.workspace.loader import WorkspacePaths


def _context(
    seed: str = "seed",
    background_events: list[BackgroundEventTableEntry] | None = None,
    threats: list[ThreatTrack] | None = None,
    turn: int = 1,
    runs_dir: Path | None = None,
    timeline: list[TimelineEntry] | None = None,
    pacing: PacingConfig | None = None,
    factions: list[FactionState] | None = None,
) -> TurnContext:
    project = ProjectConfig(
        id="p",
        title="P",
        genre="g",
        tone="t",
        autonomy_level="auto",
        user_mode="watcher",
        random_seed=seed,
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock"),
        workspace=WorkspaceConfig(root=".", state="state", runs="runs", exports="exports"),
    )
    paths = (
        WorkspacePaths(
            root=runs_dir, state=runs_dir / "state", runs=runs_dir, exports=runs_dir / "exports"
        )
        if runs_dir is not None
        else None
    )
    return TurnContext(
        turn=turn,
        project=project,
        paths=paths,
        bundle=WorldStateBundle(
            world=WorldState(
                id="world_001",
                name="World",
                summary="",
                background_events=background_events or [],
                threats=threats or [],
                pacing=pacing or PacingConfig(),
            ),
            factions=factions or [],
            timeline=timeline or [],
        ),
        random_engine=RandomEngine(seed),
    )


def test_world_simulator_returns_visibility_on_background_event():
    events = simulate_world(_context(), [])

    assert events[0].visibility == "reader"


def test_world_simulator_uses_weighted_table_roll():
    events = simulate_world(_context(), [])

    assert events[0].effects["_roll"]["type"] == "table"
    assert events[0].effects["_roll"]["table"]["table"] == "background_events"


def test_world_simulator_is_deterministic_with_fixed_seed():
    assert simulate_world(_context("same"), []) == simulate_world(_context("same"), [])


def test_background_event_visibility_is_required():
    with pytest.raises(ValidationError):
        BackgroundEventCandidate.model_validate({"description": "missing visibility"})


def test_background_event_uses_world_state_table_when_populated():
    table = [
        BackgroundEventTableEntry(text="霧が濃くなる", weight=5),
        BackgroundEventTableEntry(text="遠くで足音がする", weight=1),
    ]

    events = simulate_world(_context(background_events=table), [])

    background_event = next(e for e in events if e.type == "background_event")
    assert background_event.text in {entry.text for entry in table}
    assert background_event.effects["_roll"]["table"]["table"] == "background_events"


def test_background_event_falls_back_to_hardcoded_entries_when_table_empty():
    events = simulate_world(_context(background_events=[]), [])

    background_event = next(e for e in events if e.type == "background_event")
    assert background_event.text in {"静かな時間が流れる", "遠くで不穏な物音がする"}


def test_world_directive_becomes_a_world_event_candidate():
    intervention = {
        "id": "int_0001",
        "type": "world_directive",
        "target": {"kind": "world"},
        "content": "雨が降り始める",
        "visibility": "reader",
    }

    events = simulate_world(_context(), [intervention])

    directive_event = next(e for e in events if e.type == "world_directive")
    assert directive_event.cause == "intervention:int_0001"
    assert directive_event.text == "雨が降り始める"
    assert directive_event.visibility == "reader"


def test_event_injection_becomes_a_world_event_candidate():
    intervention = {
        "id": "int_0002",
        "type": "event_injection",
        "target": {"kind": "world"},
        "content": "見知らぬ男が現れる",
        "visibility": "reader",
    }

    events = simulate_world(_context(), [intervention])

    assert any(e.type == "event_injection" and e.cause == "intervention:int_0002" for e in events)


def test_dice_roll_request_performs_a_roll_and_carries_it_for_recording():
    intervention = {
        "id": "int_0003",
        "type": "dice_roll_request",
        "target": {"kind": "roll"},
        "content": "気づくかどうか",
        "constraints": {"notation": "2d6", "target": 7},
        "visibility": "gm_only",
    }

    events = simulate_world(_context(), [intervention])

    roll_event = next(e for e in events if e.type == "dice_roll_request")
    assert roll_event.cause == "intervention:int_0003"
    assert roll_event.effects["_roll"]["dice"]["notation"] == "2d6"


def test_character_check_derives_named_stat_and_skill_modifiers():
    context = _context()
    context.bundle = context.bundle.model_copy(
        update={
            "characters": [
                CharacterState(
                    id="char_001",
                    name="葵",
                    role="investigator",
                    stats={"知力": 12},
                    skills={"観察": 8},
                )
            ]
        }
    )
    intervention = {
        "id": "int_0004",
        "type": "dice_roll_request",
        "target": {"kind": "character", "id": "char_001"},
        "content": "手掛かりに気づくか",
        "constraints": {"target": 45, "stat": "知力", "skill": "観察"},
        "visibility": "gm_only",
    }

    events = simulate_world(context, [intervention])

    event = next(candidate for candidate in events if candidate.type == "dice_roll_request")
    roll = event.effects["_roll"]
    assert roll["type"] == "chance"
    assert roll["chance"]["base_chance"] == 45
    assert roll["chance"]["modifiers"] == {"stat:知力": 12, "skill:観察": 8}
    assert roll["chance"]["final_chance"] == 65
    assert event.effects["roll_id"] == roll["id"]
    assert event.target_id == "char_001"


@pytest.mark.parametrize("target", [0, 100])
def test_character_check_accepts_target_boundaries(target):
    context = _context()
    context.bundle = context.bundle.model_copy(
        update={
            "characters": [
                CharacterState(id="char_001", name="葵", role="investigator", stats={"知力": 5})
            ]
        }
    )
    intervention = {
        "id": "int_0005",
        "type": "dice_roll_request",
        "target": {"kind": "character", "id": "char_001"},
        "content": "境界値判定",
        "constraints": {"target": target, "stat": "知力"},
        "visibility": "gm_only",
    }

    event = next(
        candidate
        for candidate in simulate_world(context, [intervention])
        if candidate.type == "dice_roll_request"
    )

    assert event.effects["_roll"]["chance"]["base_chance"] == target


@pytest.mark.parametrize(
    ("target_id", "constraints", "message"),
    [
        ("char_999", {"target": 50, "stat": "知力"}, "character not found"),
        ("char_001", {"target": 50, "stat": "体力"}, "stat not found"),
        ("char_001", {"target": 50, "skill": "隠密"}, "skill not found"),
        ("char_001", {"target": -1, "stat": "知力"}, "target must be from 0 to 100"),
        ("char_001", {"target": 101, "stat": "知力"}, "target must be from 0 to 100"),
        ("char_001", {"target": "50", "stat": "知力"}, "target must be an integer"),
    ],
)
def test_character_check_rejects_missing_or_invalid_values(target_id, constraints, message):
    context = _context()
    context.bundle = context.bundle.model_copy(
        update={
            "characters": [
                CharacterState(
                    id="char_001",
                    name="葵",
                    role="investigator",
                    stats={"知力": 5},
                    skills={"観察": 4},
                )
            ]
        }
    )
    intervention = {
        "id": "int_0006",
        "type": "dice_roll_request",
        "target": {"kind": "character", "id": target_id},
        "content": "不正な判定",
        "constraints": constraints,
        "visibility": "gm_only",
    }

    with pytest.raises(ValueError, match=message):
        simulate_world(context, [intervention])


def test_character_check_is_reproducible_with_fixed_seed():
    intervention = {
        "id": "int_0007",
        "type": "dice_roll_request",
        "target": {"kind": "character", "id": "char_001"},
        "content": "再現可能な判定",
        "constraints": {"target": 55, "skill": "観察"},
        "visibility": "gm_only",
    }

    def run_check():
        context = _context("fixed-seed")
        context.bundle = context.bundle.model_copy(
            update={
                "characters": [
                    CharacterState(
                        id="char_001", name="葵", role="investigator", skills={"観察": 7}
                    )
                ]
            }
        )
        return next(
            candidate.effects["_roll"]
            for candidate in simulate_world(context, [intervention])
            if candidate.type == "dice_roll_request"
        )

    assert run_check() == run_check()


def test_unrelated_intervention_types_do_not_produce_world_events():
    intervention = {
        "id": "int_0004",
        "type": "character_directive",
        "target": {"kind": "character"},
    }

    events = simulate_world(_context(), [intervention])

    assert all(e.type != "character_directive" for e in events)


# Issue 008: threat escalation tracks.


def _pressure_roll(seed: str = "seed", turn: int = 1) -> int:
    """The pressure roll a fresh 2d6 threat produces for a given seed/turn (0 starting pressure
    makes the resulting ``pressure`` effect equal to the raw roll)."""
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")
    events = simulate_world(_context(seed, threats=[threat], turn=turn), [])
    return next(e for e in events if e.type == "threat_pressure").effects["pressure"]


def test_no_threats_produces_no_threat_events():
    events = simulate_world(_context(), [])

    assert all(e.type not in {"threat_pressure", "threat_stage"} for e in events)


# Issue 017: faction state runtime.


def test_no_factions_produces_no_faction_move_events():
    events = simulate_world(_context(), [])

    assert all(e.type != "faction_move" for e in events)


def test_world_simulator_emits_one_faction_move_for_first_faction():
    faction_a = FactionState(
        id="faction_001",
        name="Mist Keepers",
        public_face="old station committee",
        resources={"secrecy": 70, "influence": 45},
        relations={"char_001": 40, "char_004": 15},
    )
    faction_b = FactionState(
        id="faction_002",
        name="Other",
        public_face="other",
        resources={"influence": 60},
        relations={"char_001": 20},
    )

    events = simulate_world(_context(factions=[faction_a, faction_b]), [])

    faction_events = [event for event in events if event.type == "faction_move"]
    assert len(faction_events) == 1
    assert faction_events[0].visibility == "gm_only"
    assert faction_events[0].effects == {
        "faction_id": "faction_001",
        "resource_deltas": {"influence": -5},
        "relation_deltas": {"char_001": 5},
    }


def test_threat_with_no_stages_emits_only_a_pressure_event():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")

    events = simulate_world(_context(threats=[threat]), [])

    assert [e.type for e in events if e.type.startswith("threat_")] == ["threat_pressure"]


def test_threat_pressure_event_is_gm_only_and_carries_the_roll():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=10, pressure_per_turn="2d6")

    events = simulate_world(_context(threats=[threat]), [])

    event = next(e for e in events if e.type == "threat_pressure")
    assert event.visibility == "gm_only"
    assert event.effects["threat_id"] == "threat_001"
    assert event.effects["_roll"]["type"] == "dice"
    assert event.effects["_roll"]["dice"]["notation"] == "2d6"
    assert event.effects["roll_id"] == event.effects["_roll"]["id"]
    assert event.effects["pressure"] == 10 + event.effects["_roll"]["result"]


def test_threat_pressure_clamps_to_100():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=99, pressure_per_turn="2d6")

    events = simulate_world(_context(threats=[threat]), [])

    event = next(e for e in events if e.type == "threat_pressure")
    assert event.effects["pressure"] == 100


def test_threat_stage_not_yet_crossed_does_not_fire():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=roll + 1, text="not yet", visibility=Visibility.SCENE)],
    )

    events = simulate_world(_context(threats=[threat]), [])

    assert [e for e in events if e.type == "threat_stage"] == []


def test_threat_stage_crossed_by_the_roll_fires_once():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=roll, text="足音が近づく", visibility=Visibility.SCENE)],
    )

    events = simulate_world(_context(threats=[threat]), [])

    stage_events = [e for e in events if e.type == "threat_stage"]
    assert len(stage_events) == 1
    assert stage_events[0].text == "足音が近づく"
    assert stage_events[0].visibility == "scene"
    assert stage_events[0].effects["threat_id"] == "threat_001"
    assert stage_events[0].effects["stage_at"] == roll
    assert (
        stage_events[0].effects["roll_id"]
        == next(e for e in events if e.type == "threat_pressure").effects["roll_id"]
    )


def test_threat_stage_carries_arbitrary_effects_like_scene_transition():
    """Issue 009: scene_transition is just another key in ThreatStage.effects (data-driven,
    no world_simulator code path dedicated to it)."""
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[
            ThreatStage(
                at=roll,
                text="追跡者が姿を現す",
                visibility=Visibility.READER,
                effects={"scene_transition": {"end": "scene_001", "start": "scene_002"}},
            )
        ],
    )

    events = simulate_world(_context(threats=[threat]), [])

    stage_event = next(e for e in events if e.type == "threat_stage")
    assert stage_event.effects["scene_transition"] == {"end": "scene_001", "start": "scene_002"}


def test_multiple_thresholds_crossed_in_one_roll_all_fire_in_ascending_order():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[
            ThreatStage(at=roll, text="second", visibility=Visibility.READER),
            ThreatStage(at=1, text="first", visibility=Visibility.SCENE),
        ],
    )

    events = simulate_world(_context(threats=[threat]), [])

    stage_events = [e for e in events if e.type == "threat_stage"]
    assert [e.text for e in stage_events] == ["first", "second"]


def test_already_past_stage_never_refires():
    roll = _pressure_roll()
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=roll,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=roll, text="already happened", visibility=Visibility.SCENE)],
    )

    events = simulate_world(_context(threats=[threat]), [])

    assert [e for e in events if e.type == "threat_stage"] == []


def test_threat_events_are_deterministic_with_fixed_seed():
    threat = ThreatTrack(
        id="threat_001",
        name="Pursuer",
        pressure=0,
        pressure_per_turn="2d6",
        stages=[ThreatStage(at=5, text="closer", visibility=Visibility.SCENE)],
    )

    first = simulate_world(_context("same-seed", threats=[threat]), [])
    second = simulate_world(_context("same-seed", threats=[threat]), [])

    assert first == second


# Issue 011: pacing/stall detection and its Simulate-phase escalation response.


def test_no_boost_and_no_pacing_event_when_pacing_is_off(tmp_path):
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")

    events = simulate_world(
        _context(threats=[threat], turn=10, runs_dir=tmp_path, pacing=PacingConfig()), []
    )

    pressure_event = next(e for e in events if e.type == "threat_pressure")
    assert pressure_event.effects["_roll"]["dice"]["notation"] == "2d6"
    assert all(e.type != "pacing_stall" for e in events)


def test_no_boost_when_turn_is_too_early_to_judge_stall(tmp_path):
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")
    pacing = PacingConfig(stall_window=3, pressure_boost=4)

    events = simulate_world(
        _context(threats=[threat], turn=3, runs_dir=tmp_path, pacing=pacing), []
    )

    pressure_event = next(e for e in events if e.type == "threat_pressure")
    assert pressure_event.effects["_roll"]["dice"]["notation"] == "2d6"
    assert all(e.type != "pacing_stall" for e in events)


def test_boost_is_appended_to_threat_notation_when_stalled(tmp_path):
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")
    pacing = PacingConfig(stall_window=3, pressure_boost=4)

    events = simulate_world(
        _context(threats=[threat], turn=4, runs_dir=tmp_path, pacing=pacing), []
    )

    pressure_event = next(e for e in events if e.type == "threat_pressure")
    assert pressure_event.effects["_roll"]["dice"]["notation"] == "2d6+4"


def test_pacing_stall_event_emitted_once_with_correct_effects(tmp_path):
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")
    pacing = PacingConfig(stall_window=3, pressure_boost=4)

    events = simulate_world(
        _context(threats=[threat], turn=4, runs_dir=tmp_path, pacing=pacing), []
    )

    stall_events = [e for e in events if e.type == "pacing_stall"]
    assert len(stall_events) == 1
    assert stall_events[0].visibility == "gm_only"
    assert stall_events[0].effects == {"stalled_turns": 3, "pressure_boost": 4}


def test_no_boost_when_recent_turn_has_an_advancement_signal(tmp_path):
    import yaml

    turn_dir = tmp_path / "turn_0003"
    turn_dir.mkdir(parents=True)
    (turn_dir / "events.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "event_0001",
                    "turn": 3,
                    "type": "threat_stage",
                    "text": "advances",
                    "visibility": "scene",
                }
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure=0, pressure_per_turn="2d6")
    pacing = PacingConfig(stall_window=3, pressure_boost=4)

    events = simulate_world(
        _context(
            threats=[threat],
            turn=4,
            runs_dir=tmp_path,
            pacing=pacing,
            timeline=[TimelineEntry(turn=3, event_ids=["event_0001"])],
        ),
        [],
    )

    pressure_event = next(e for e in events if e.type == "threat_pressure")
    assert pressure_event.effects["_roll"]["dice"]["notation"] == "2d6"
    assert all(e.type != "pacing_stall" for e in events)
