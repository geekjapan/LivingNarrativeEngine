"""50-turn mock regression fixture (docs/issues/019): the Phase 5 "50+ turns without breaking
down" + "a regression fixture that can catch quality regressions" gate. Extends the 20-turn
smoke test's approach (mock provider, fixed seed, fully deterministic, review-gate handling
for the pursuer's threat-stage-100 scene transition) to 50 turns, then asserts long-run
invariants via ``session.metrics.collect_metrics`` instead of hand-picked artifact checks.

The narrator's ``memory_summary_update`` (Issue 015) is an LLM-only structured-output field:
the mock provider (``llm/mock.py``) always fills *optional* fields with their pydantic default
(``None``/``[]``) -- only *required* fields (e.g. ``prose``) get synthetic content (see
``MockProvider.complete``/``generate_value``). A plain mock-provider run would therefore never
produce a single memory summary, no matter how many turns run. Since the memory-summary
cadence is exactly the kind of long-run invariant this fixture exists to guard,
``run_narrate_phase`` is wrapped to backfill ``memory_summary_update`` whenever
``context.memory_summary_due`` is true and the (mocked) narrator left it null -- doing exactly
what a real LLM narrator is asked to (see ``llm_narrator.py``'s prompt), without faking
anything else about the turn.
"""

import time

import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus
from living_narrative.pipeline import driver as driver_module
from living_narrative.session.metrics import collect_metrics
from living_narrative.session.review import ReviewDecision, resolve_review
from living_narrative.workspace.init import create_project

FIXED_SEED = "mist-station-smoke-50-fixed-seed"
TURN_COUNT = 50
MEMORY_SUMMARY_INTERVAL = 10  # mist_station template's world.yaml memory_summary_interval
WALL_CLOCK_BUDGET_SECONDS = 60


def _load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _pin_seed(project_path) -> None:
    data = _load_yaml(project_path)
    data["random_seed"] = FIXED_SEED
    project_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _make_memory_summary_backfill(real_run_narrate_phase):
    """Wraps the real ``run_narrate_phase`` (captured before monkeypatching, to dodge the
    ``narration`` <-> ``pipeline`` import cycle a module-level import would trigger here) so a
    memory summary is written whenever one is due, regardless of what the mock provider left
    optional (see module docstring)."""

    def _backfill_memory_summary(*, gateway, project, context, style, mood, tone_control):
        result, meta = real_run_narrate_phase(
            gateway=gateway,
            project=project,
            context=context,
            style=style,
            mood=mood,
            tone_control=tone_control,
        )
        if context.memory_summary_due and not result.memory_summary_update:
            result = result.model_copy(
                update={
                    "memory_summary_update": f"turn {context.turn}までの通史要約(smoke synthetic)。"
                }
            )
        return result, meta

    return _backfill_memory_summary


def _run_turns(pipeline, project_path, turn_range, results):
    workspace_root = project_path.parent / "workspace"
    state_dir = workspace_root / "state"
    for turn in turn_range:
        result = pipeline.run(project_path)
        assert result.turn == turn
        if result.status in (TurnStatus.STOPPED_FOR_REVIEW, TurnStatus.PENDING_REVIEW):
            # Same review-gate path as the 20-turn smoke test (tests/smoke/
            # test_mist_station_20_turns.py): the pursuer's threat stage 100 fires a
            # scene_transition, tripping the unconditional SCENE_END stop (D119). A GM
            # accepts the diff so the deterministic run keeps progressing.
            resolve_review(
                workspace_root=workspace_root,
                state_dir=state_dir,
                turn_dir=result.turn_dir,
                decision=ReviewDecision.ACCEPT_ALL,
                decided_by="full_gm",
            )
        else:
            assert result.status == TurnStatus.APPLIED, (
                f"turn {turn} did not apply cleanly: status={result.status}"
            )
        results.append(result)


def test_50_turn_mist_station_regression(tmp_path, monkeypatch):
    monkeypatch.setattr(
        driver_module,
        "run_narrate_phase",
        _make_memory_summary_backfill(driver_module.run_narrate_phase),
    )

    project_path = create_project(
        tmp_path / "mist_station", title="霧の駅", template="mist_station"
    )
    _pin_seed(project_path)

    results: list = []
    start = time.monotonic()
    _run_turns(TurnPipeline(), project_path, range(1, TURN_COUNT + 1), results)
    elapsed = time.monotonic() - start

    assert [r.turn for r in results] == list(range(1, TURN_COUNT + 1))
    assert elapsed < WALL_CLOCK_BUDGET_SECONDS, (
        f"{TURN_COUNT} mock turns took {elapsed:.1f}s (budget: {WALL_CLOCK_BUDGET_SECONDS}s)"
    )

    metrics = collect_metrics(project_path)

    # All turns applied (review-gate turns included, once resolved); timeline matches 1:1.
    assert metrics.turns.total == TURN_COUNT
    assert metrics.turns.timeline_entries == TURN_COUNT
    assert metrics.turns.by_status == {"applied": TURN_COUNT}
    assert metrics.turns.discarded == 0
    assert metrics.turns.rolledback == 0

    # No checker errors anywhere across the run.
    assert metrics.checks.by_severity.get("error", 0) == 0

    # Every final emotion is in range, and no emotion is pinned at the 100 ceiling for 10+
    # consecutive turns (a stuck-emotion regression) whenever its trajectory is reconstructable
    # (the character has an `emotions_baseline` entry for it -- true for every mist_station
    # character/emotion, see the template's characters/*.yaml).
    for character in metrics.emotions:
        for emotion in character.emotions:
            assert 0 <= emotion.final <= 100
            if emotion.max_consecutive_at_ceiling is not None:
                assert emotion.max_consecutive_at_ceiling < 10

    # mist_station's single threat (threat_001, world.yaml) crosses its only
    # scene_transition-bearing stage (pressure >= 100) exactly once within 50 turns: scene_001
    # ends, scene_002 becomes active, and that stage never fires again once pressure is already
    # >= 100. So exactly one scene is active at the end (confirmed by an unmonkeypatched run at
    # this fixed seed -- never 0, never 2+). `transition_count` is 2 because a single transition
    # is two diff changes (end scene_001 + start scene_002).
    assert metrics.scenes.transition_count == 2
    assert metrics.scenes.final_active_count == 1
    assert metrics.scenes.final_active_scene_ids == ["scene_002"]

    # Issue 015: a memory summary every `memory_summary_interval` (10) turns, no more no less.
    assert metrics.memory.summary_count == TURN_COUNT // MEMORY_SUMMARY_INTERVAL
