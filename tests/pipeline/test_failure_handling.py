import multiprocessing as mp
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from living_narrative.llm.errors import StructuredOutputError
from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.session.review import ReviewDecision, resolve_review
from living_narrative.session.rollback import execute_rollback, plan_rollback
from living_narrative.state.store import StateStore
from living_narrative.workspace.backup import create_backup
from living_narrative.workspace.loader import load_project


def _install_lock_holder(kind, locked, release):
    if kind == "turn":
        import living_narrative.pipeline.driver as module
    elif kind == "review":
        import living_narrative.session.review as module
    elif kind == "rollback":
        import living_narrative.session.rollback as module
    else:
        import living_narrative.workspace.backup as module

    original_lock = module.project_lock

    @contextmanager
    def hold_lock(project_root):
        with original_lock(project_root):
            locked.set()
            if not release.wait(10):
                raise RuntimeError("test lock release timed out")
            yield

    module.project_lock = hold_lock


def _run_mutation_worker(
    kind,
    project_path,
    turn_dir,
    rollback_plan,
    backup_output,
    locked,
    release,
    hold,
    result_queue,
):
    if hold:
        _install_lock_holder(kind, locked, release)
    try:
        project_path = Path(project_path)
        if kind == "turn":
            result = TurnPipeline().run(project_path)
            result_queue.put(("ok", result.turn, result.status.value))
        elif kind == "review":
            paths = load_project(project_path).paths
            result = resolve_review(
                workspace_root=paths.root,
                state_dir=paths.state,
                turn_dir=Path(turn_dir),
                decision=ReviewDecision.ACCEPT_ALL,
                decided_by="god",
            )
            result_queue.put(("ok", result.resulting_turn_status.value))
        elif kind == "rollback":
            paths = load_project(project_path).paths
            result = execute_rollback(paths, rollback_plan)
            result_queue.put(("ok", result.to_turn))
        else:
            result = create_backup(
                project_path,
                Path(backup_output),
                created_at=datetime(2026, 7, 13, tzinfo=UTC),
            )
            result_queue.put(("ok", str(result)))
    except BaseException as exc:  # noqa: BLE001 - report child failures to the parent
        result_queue.put(("error", type(exc).__name__, str(exc)))


def _join_worker(process, result_queue):
    process.join(10)
    assert not process.is_alive()
    return result_queue.get(timeout=2)


def test_unregistered_renderer_style_fails_turn_and_keeps_partial_artifacts(
    tmp_path, build_project
):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path, renderer_style="script")

    assert result.status == TurnStatus.FAILED
    assert (result.turn_dir / "intervention.yaml").exists()
    assert (result.turn_dir / "events.yaml").exists()
    assert (result.turn_dir / "rolls.yaml").exists()
    assert not (result.turn_dir / "narration.md").exists()
    assert not (result.turn_dir / "checks.yaml").exists()
    assert not (result.turn_dir / "state_diff.yaml").exists()

    meta = yaml.safe_load((result.turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["status"] == "failed"
    assert meta["error"]["phase"] == "narrate"
    assert "script" in meta["error"]["message"]


def test_llm_provider_typed_exception_fails_act_phase(tmp_path, build_project):
    project_path = build_project(tmp_path)
    registry = default_registry()

    def failing_act(context, world_events, gateway, interventions=(), past_events=None):
        raise StructuredOutputError(
            provider_name="mock", model="mock-v1", schema_name="X", last_error="boom"
        )

    registry.register("act", failing_act)

    result = TurnPipeline(registry=registry).run(project_path)

    assert result.status == TurnStatus.FAILED
    meta = yaml.safe_load((result.turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["error"]["phase"] == "act"
    assert meta["error"]["exception_type"] == "StructuredOutputError"


@pytest.mark.parametrize("competitor", ["turn", "review", "rollback", "backup"])
def test_mutation_matrix_is_process_locked(tmp_path, build_project, competitor):
    project_path = build_project(tmp_path / competitor)
    turn_dir = None
    rollback_plan = None
    if competitor == "review":
        pending = TurnPipeline().run(project_path, commit_mode="review")
        turn_dir = pending.turn_dir
    elif competitor == "rollback":
        applied = TurnPipeline().run(project_path)
        assert applied.status is TurnStatus.APPLIED
        paths = load_project(project_path).paths
        rollback_plan = plan_rollback(paths.runs, to_turn=0)

    context = mp.get_context("fork")
    locked = context.Event()
    release = context.Event()
    holder_queue = context.Queue()
    competitor_queue = context.Queue()
    backup_output = tmp_path / f"backups-{competitor}"
    args = (
        "turn",
        str(project_path),
        str(turn_dir) if turn_dir is not None else None,
        rollback_plan,
        str(backup_output),
        locked,
        release,
    )
    holder = context.Process(target=_run_mutation_worker, args=(*args, True, holder_queue))
    holder.start()
    assert locked.wait(10)

    competitor_process = context.Process(
        target=_run_mutation_worker,
        args=(
            competitor,
            str(project_path),
            str(turn_dir) if turn_dir is not None else None,
            rollback_plan,
            str(backup_output),
            context.Event(),
            context.Event(),
            False,
            competitor_queue,
        ),
    )
    competitor_process.start()
    competitor_result = _join_worker(competitor_process, competitor_queue)
    release.set()
    holder_result = _join_worker(holder, holder_queue)

    assert competitor_result[0:2] == ("error", "ProjectLockError")
    if competitor == "review":
        assert holder_result[0:2] == ("error", "UnresolvedTurnError")
    else:
        assert holder_result[0] == "ok"

    paths = load_project(project_path).paths
    StateStore.load(paths.state)
    turn_dirs = sorted(path for path in paths.runs.glob("turn_[0-9]*") if path.is_dir())
    turn_numbers = [int(path.name.removeprefix("turn_")) for path in turn_dirs]
    assert len(turn_numbers) == len(set(turn_numbers))
    applied_meta = [
        yaml.safe_load((path / "meta.yaml").read_text(encoding="utf-8"))
        for path in turn_dirs
        if (path / "meta.yaml").exists()
    ]
    offsets = [meta["rng_start_offset"] for meta in applied_meta if meta.get("status") == "applied"]
    assert offsets == sorted(set(offsets))
    if competitor == "backup":
        assert not backup_output.exists()
