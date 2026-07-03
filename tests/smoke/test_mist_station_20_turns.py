"""20-turn smoke test (cli/spec.md "サンプル世界での20ターンスモークテスト"): regresses the
project plan's §21.4 MVP success condition (10-20 turns without breaking down), exercising
its upper bound. Mock provider + a fixed ``random_seed``, no network, fully deterministic.
"""

import yaml

from living_narrative.export_replay import assemble_replay
from living_narrative.pipeline import TurnPipeline, TurnStatus
from living_narrative.workspace.init import create_project

FIXED_SEED = "mist-station-smoke-fixed-seed"

TURN_3_INTERVENTION = {
    "type": "character_directive",
    "target": {"kind": "character", "id": "char_002"},
    "content": "足音のする方向を確かめに歩み寄る",
    "visibility": "scene",
}
TURN_6_INTERVENTION = {
    "type": "scene_directive",
    "target": {"kind": "scene", "id": "scene_001"},
    "content": "緊張感を一段と高める",
    "visibility": "scene",
}


def _load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _pin_seed(project_path) -> None:
    data = _load_yaml(project_path)
    data["random_seed"] = FIXED_SEED
    project_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _run_turns(pipeline, project_path, turn_range, drafts_by_turn, results):
    for turn in turn_range:
        result = pipeline.run(project_path, intervention_drafts=drafts_by_turn.get(turn))
        assert result.turn == turn
        assert result.status == TurnStatus.APPLIED, (
            f"turn {turn} did not apply cleanly: status={result.status}"
        )
        results.append(result)


def test_20_turn_mist_station_smoke(tmp_path):
    project_path = create_project(
        tmp_path / "mist_station", title="霧の駅", template="mist_station"
    )
    _pin_seed(project_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    drafts_by_turn = {3: [TURN_3_INTERVENTION], 6: [TURN_6_INTERVENTION]}

    results = []
    _run_turns(TurnPipeline(), project_path, range(1, 6), drafts_by_turn, results)

    # Snapshot turns 1-5 byte-for-byte before "resuming" (6).
    snapshot = {path: path.read_bytes() for path in sorted(runs_dir.rglob("*")) if path.is_file()}

    # (6) Resume: a brand-new TurnPipeline (as a fresh CLI invocation would construct)
    # continues from turn 6 using only what's on disk — no in-memory state carried over.
    _run_turns(TurnPipeline(), project_path, range(6, 21), drafts_by_turn, results)

    # (1) All 20 turns completed without ever going `failed`.
    assert [r.turn for r in results] == list(range(1, 21))

    # (6, cont'd) Turns 1-5's artifacts are untouched by the resumed run.
    for path, content in snapshot.items():
        assert path.read_bytes() == content, f"{path} changed after resume"

    # (2) The turn 3 / turn 6 interventions were recorded and fed into that turn's own
    # Simulate phase (agent_io/simulate.yaml's `input.interventions`) — the exact point
    # at which they take effect on that turn's world/character/narration processing.
    for turn, expected in ((3, TURN_3_INTERVENTION), (6, TURN_6_INTERVENTION)):
        turn_dir = runs_dir / f"turn_{turn:04d}"
        intervention_data = _load_yaml(turn_dir / "intervention.yaml")
        assert any(
            item["content"] == expected["content"] for item in intervention_data["interventions"]
        )
        simulate_data = _load_yaml(turn_dir / "agent_io" / "simulate.yaml")
        assert any(
            item["content"] == expected["content"]
            for item in simulate_data["input"]["interventions"]
        )

    # (3) At least one turn recorded >=1 roll.
    assert any(_load_yaml(runs_dir / f"turn_{n:04d}" / "rolls.yaml") for n in range(1, 21))

    # (4) Every turn's state diff was saved and applied (auto-apply path).
    for n in range(1, 21):
        diff_data = _load_yaml(runs_dir / f"turn_{n:04d}" / "state_diff.yaml")
        assert diff_data["applied"] is True

    # (5) No error-level leak-checker findings across all 20 turns.
    for n in range(1, 21):
        checks = _load_yaml(runs_dir / f"turn_{n:04d}" / "checks.yaml")
        leak_errors = [
            f for f in checks["findings"] if f["source"] == "leak" and f["severity"] == "error"
        ]
        assert not leak_errors, f"turn {n} had leak errors: {leak_errors}"

    # (7) export replay never contains any of the 3 gm_vault hidden truths verbatim.
    replay_content = assemble_replay(runs_dir, style="novel")
    gm_vault = _load_yaml(project_path.parent / "workspace" / "state" / "gm_vault.yaml")
    for entry in gm_vault:
        assert entry["text"] not in replay_content
