import yaml

from living_narrative.agents.character import run_character_agent
from living_narrative.narration.models import NarrationResult, NarratorQuestUpdateCandidate
from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.pipeline.models import ActionCandidate
from living_narrative.session.metrics import collect_metrics
from living_narrative.session.review import ReviewDecision, resolve_review
from living_narrative.workspace.init import create_project


def _load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_player_character_game_features_coexist_in_one_mock_session(tmp_path, monkeypatch):
    from living_narrative.pipeline import driver as driver_module

    project_path = create_project(
        tmp_path / "mist_station", title="霧の駅", template="mist_station"
    )
    project = _load_yaml(project_path)
    project.update({"user_mode": "player_character", "player_char_id": "char_001"})
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    state_dir = project_path.parent / "workspace" / "state"
    for character_id in ("char_001", "char_002"):
        path = state_dir / "characters" / f"{character_id}.yaml"
        character = _load_yaml(path)
        character.setdefault("stats", {})["hp"] = 10
        path.write_text(
            yaml.safe_dump(character, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    registry = default_registry()

    def game_act(context, world_events, gateway, interventions, **kwargs):
        actions, records = run_character_agent(
            context, world_events, gateway, interventions, **kwargs
        )
        if context.turn == 1:
            actions.append(
                ActionCandidate(
                    character_id="char_001",
                    action_text="追跡者を退ける",
                    target_id="char_002",
                    effects={
                        "combat": {
                            "attacker": "char_001",
                            "defender": "char_002",
                            "stakes": "出口への退路を守る",
                            "stat": "体力",
                            "skill": "探索",
                            "target": 100,
                            "damage": 2,
                        }
                    },
                )
            )
        return actions, records

    registry.register("act", game_act)

    quest_updates = {
        1: [NarratorQuestUpdateCandidate(action="advance", quest_id="quest_001")],
        2: [NarratorQuestUpdateCandidate(action="resolve", quest_id="quest_001")],
        3: [
            NarratorQuestUpdateCandidate(
                action="open", quest_id="quest_002", title="子どもの切符を調べる"
            )
        ],
    }

    def narrate(*, context, **kwargs):
        return (
            NarrationResult(
                text=f"PCの行動を調停したターン{context.turn}。",
                style="novel",
                quest_updates=quest_updates[context.turn],
            ),
            {"mode": "mock", "style": "novel"},
        )

    monkeypatch.setattr(driver_module, "run_narrate_phase", narrate)
    pipeline = TurnPipeline(registry=registry)
    drafts = [
        [
            {
                "type": "character_directive",
                "target": {"kind": "character", "id": "char_001"},
                "content": "懐中電灯を使い、追跡者へ踏み込む",
                "constraints": {"inventory_action": "use", "item_id": "item_001", "qty": 1},
                "visibility": "character",
            },
            {
                "type": "dice_roll_request",
                "target": {"kind": "character", "id": "char_001"},
                "content": "霧の切れ目を見抜く",
                "constraints": {"target": 100, "stat": "知力", "skill": "観察"},
                "visibility": "character",
            },
        ],
        [
            {
                "type": "character_directive",
                "target": {"kind": "character", "id": "char_001"},
                "content": "出口の標識を確かめる",
                "constraints": {},
                "visibility": "character",
            }
        ],
        [
            {
                "type": "character_directive",
                "target": {"kind": "character", "id": "char_001"},
                "content": "古い切符を拾う",
                "constraints": {},
                "visibility": "character",
            }
        ],
    ]

    results = []
    for turn in drafts:
        result = pipeline.run(project_path, intervention_drafts=turn)
        if result.status == TurnStatus.STOPPED_FOR_REVIEW:
            resolve_review(
                workspace_root=project_path.parent / "workspace",
                state_dir=state_dir,
                turn_dir=result.turn_dir,
                decision=ReviewDecision.ACCEPT_ALL,
                decided_by="full_gm",
            )
        else:
            assert result.status == TurnStatus.APPLIED
        results.append(result)

    metrics = collect_metrics(project_path).game
    assert metrics.combat_count == 1
    assert (metrics.quest_opened, metrics.quest_advanced, metrics.quest_resolved) == (1, 1, 1)
    assert metrics.applied_pc_action_count == 3
    # Template recurrence prevents the same encounter from firing every turn.
    assert metrics.encounter_count == 1
    assert (metrics.skill_check_successes, metrics.skill_check_total) == (1, 1)
    assert metrics.skill_check_success_rate == 1.0

    turn1 = results[0].turn_dir
    events = _load_yaml(turn1 / "events.yaml")
    rolls = _load_yaml(turn1 / "rolls.yaml")
    diff = _load_yaml(turn1 / "state_diff.yaml")
    combat = next(event for event in events if event["type"] == "combat")
    check = next(event for event in events if event["type"] == "dice_roll_request")
    interventions = _load_yaml(turn1 / "intervention.yaml")["interventions"]
    check_intervention = next(item for item in interventions if item["type"] == "dice_roll_request")
    assert set(combat["roll_ids"]).issubset({roll["id"] for roll in rolls})
    assert check["effects"]["roll_id"] in {roll["id"] for roll in rolls}
    assert check["cause"] == f"intervention:{check_intervention['id']}"
    assert diff["applied"] is True
    assert any(
        change["target"] == "character"
        and change["op"] == "remove"
        and change["path"] == "inventory"
        and change["value"] == {"id": "item_001"}
        for change in diff["diff"]["changes"]
    )
    assert any(change["target"] == "quests" for change in diff["diff"]["changes"])
    assert all(
        event["id"]
        in {
            entry for item in _load_yaml(state_dir / "timeline.yaml") for entry in item["event_ids"]
        }
        for event in events
    )

    pc_record = next(
        record
        for record in _load_yaml(turn1 / "agent_io" / "act.yaml")
        if record["character_id"] == "char_001"
    )
    serialized_scope = yaml.safe_dump(pc_record["input_context"], allow_unicode=True)
    assert "駅の最深部には、かつて何かを封じるために" not in serialized_scope
    assert "あの日見たものの正体を、まだリナに話せていない" not in serialized_scope
    assert "守り手の一族の末裔" not in serialized_scope
