"""TurnPipeline: drives the 8 phases in order (spec-foundation.md §6)."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from living_narrative.intervention.history import append_history, build_history_entries
from living_narrative.intervention.ids import make_intervention_id_allocator
from living_narrative.intervention.permissions import PermissionTable
from living_narrative.intervention.router import resolve_tone_control
from living_narrative.intervention.service import run_intervene_phase
from living_narrative.narration.context import build_narrator_context
from living_narrative.narration.narrator import narrate
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.errors import LoadError
from living_narrative.pipeline.ids import make_event_id_allocator
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.pipeline.models import ErrorReport, InterventionFile
from living_narrative.pipeline.registry import SlotRegistry, default_registry
from living_narrative.pipeline.rng_state import load_all_rolls, total_rng_draws_consumed
from living_narrative.pipeline.status import TurnStatus
from living_narrative.pipeline.turn_numbering import (
    determine_next_turn_number,
    discard_turn_directory,
    turn_dir_path,
)
from living_narrative.pipeline.writer import (
    build_meta_dict,
    make_roll_recorder,
    write_agent_io,
    write_agent_io_component,
    write_checks,
    write_events,
    write_intervention,
    write_meta,
    write_narration,
    write_state_diff,
)
from living_narrative.random.engine import RandomEngine, load_rolls, next_roll_number
from living_narrative.session.mode import session_permission_table
from living_narrative.session.review import write_review_yaml
from living_narrative.session.stop_conditions import evaluate_stop_conditions
from living_narrative.state.diff import apply_state_diff
from living_narrative.state.models import SceneStatus, UserMode
from living_narrative.state.store import StateLoadError, StateStore
from living_narrative.workspace.loader import load_project

CommitMode = Literal["auto", "review"]


@dataclass(frozen=True)
class TurnRunResult:
    turn: int
    status: TurnStatus
    turn_dir: Path


def _active_scene_mood(bundle) -> str:
    for scene in bundle.scenes:
        if scene.status == SceneStatus.ACTIVE:
            return scene.mood
    return ""


def _format_issues(issues) -> str:
    return "; ".join(f"{issue.path}[{issue.field}]: {issue.message}" for issue in issues)


@contextmanager
def _timed_phase(name: str, durations: dict[str, float], current: list[str]):
    current[0] = name
    started = perf_counter()
    try:
        yield
    finally:
        durations[name] = perf_counter() - started


class TurnPipeline:
    """Drives Load -> Intervene -> Simulate -> Act -> Resolve -> Narrate -> (BuildDiff) ->
    Check -> Commit for a single turn, writing artifacts under ``workspace/runs/turn_NNNN/``.
    """

    def __init__(self, registry: SlotRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def run(
        self,
        project_path: Path,
        *,
        commit_mode: CommitMode = "auto",
        renderer_style: str | None = None,
        mood_override: str | None = None,
        tone_control: str | None = None,
        intervention_text: str | None = None,
        intervention_drafts: list[dict[str, Any]] | None = None,
        permission_table: PermissionTable | None = None,
    ) -> TurnRunResult:
        if commit_mode not in ("auto", "review"):
            raise ValueError(f"invalid commit_mode: {commit_mode!r}")

        read = load_project(project_path)
        if not read.is_valid:
            raise LoadError(f"invalid project at {project_path}: {_format_issues(read.errors)}")
        paths = read.paths
        project = read.config

        turn = determine_next_turn_number(paths.runs)
        turn_dir = turn_dir_path(paths.runs, turn)
        if turn_dir.exists():
            discard_turn_directory(turn_dir)

        durations: dict[str, float] = {}
        load_started = perf_counter()
        try:
            bundle = StateStore.load(paths.state)
        except StateLoadError as exc:
            raise LoadError(
                f"invalid state at {paths.state}: {_format_issues(exc.issues)}"
            ) from exc
        durations["load"] = perf_counter() - load_started

        initial_rng_offset = total_rng_draws_consumed(paths.runs)
        engine = RandomEngine(
            project.random_seed,
            draws_consumed=initial_rng_offset,
            next_roll_number=next_roll_number(load_all_rolls(paths.runs)),
        )
        context = TurnContext(
            turn=turn, project=project, paths=paths, bundle=bundle, random_engine=engine
        )
        gateway = LLMGateway(project=project, random_seed=project.random_seed)

        turn_dir.mkdir(parents=True, exist_ok=True)
        current_phase = ["intervene"]
        status = TurnStatus.FAILED
        error: ErrorReport | None = None

        try:
            with _timed_phase("intervene", durations, current_phase):
                allocate_intervention_id = make_intervention_id_allocator(paths.runs)
                effective_permission_table = permission_table or session_permission_table()
                intervene_result = run_intervene_phase(
                    gateway=gateway,
                    turn=turn,
                    user_role=project.user_mode,
                    allocate_id=allocate_intervention_id,
                    permission_table=effective_permission_table,
                    free_text=intervention_text,
                    direct_drafts=intervention_drafts,
                )
                intervention_file = InterventionFile(
                    turn=turn,
                    interventions=[
                        item.model_dump(mode="json") for item in intervene_result.interventions
                    ],
                    rejections=[
                        item.model_dump(mode="json") for item in intervene_result.rejections
                    ],
                )
                write_intervention(turn_dir, intervention_file)

            with _timed_phase("simulate", durations, current_phase):
                world_events = self.registry.get("simulate")(
                    context, intervention_file.interventions
                )
                write_agent_io_component(
                    turn_dir,
                    "simulate",
                    {
                        "input": {"interventions": intervention_file.interventions},
                        "output": [item.model_dump(mode="json") for item in world_events],
                    },
                )

            with _timed_phase("act", durations, current_phase):
                action_candidates, act_records = self.registry.get("act")(
                    context, world_events, gateway, intervention_file.interventions
                )
                write_agent_io(turn_dir, act_records)
                write_agent_io_component(
                    turn_dir,
                    "act_candidates",
                    [item.model_dump(mode="json") for item in action_candidates],
                )

            with _timed_phase("resolve", durations, current_phase):
                allocate_event_id = make_event_id_allocator(paths.runs)
                record_roll = make_roll_recorder(turn_dir)
                resolved_events = self.registry.get("resolve")(
                    context, world_events, action_candidates, allocate_event_id, record_roll
                )
                write_agent_io_component(
                    turn_dir,
                    "resolve",
                    {
                        "input": {
                            "world_events": [item.model_dump(mode="json") for item in world_events],
                            "action_candidates": [
                                item.model_dump(mode="json") for item in action_candidates
                            ],
                        },
                        "output": [item.model_dump(mode="json") for item in resolved_events],
                    },
                )
                write_events(turn_dir, resolved_events)

            with _timed_phase("narrate", durations, current_phase):
                style = renderer_style or project.renderer
                narrator_context = build_narrator_context(
                    context, resolved_events, intervention_file.interventions
                )
                mood = mood_override if mood_override is not None else _active_scene_mood(bundle)
                effective_tone_control = resolve_tone_control(
                    intervention_file.interventions, tone_control
                )
                narration = narrate(
                    narrator_context, style=style, mood=mood, tone_control=effective_tone_control
                )
                write_narration(turn_dir, turn, narration.style, narration.text)

            with _timed_phase("build_diff", durations, current_phase):
                build_diff_output = self.registry.get("build_diff")(
                    context, resolved_events, intervention_file.interventions, allocate_event_id
                )
                if build_diff_output.synthetic_events:
                    resolved_events = [*resolved_events, *build_diff_output.synthetic_events]
                    write_events(turn_dir, resolved_events)
                write_agent_io_component(
                    turn_dir,
                    "build_diff",
                    build_diff_output.model_dump(mode="json"),
                )

            with _timed_phase("check", durations, current_phase):
                check_results = self.registry.get("check")(
                    context, narration.text, resolved_events, build_diff_output.diff
                )
                write_agent_io_component(
                    turn_dir,
                    "check",
                    [item.model_dump(mode="json") for item in check_results],
                )
                write_checks(turn_dir, check_results)

            with _timed_phase("commit", durations, current_phase):
                has_error = any(result.severity == "error" for result in check_results)
                stop_conditions = evaluate_stop_conditions(
                    project=project,
                    autonomy_level=project.autonomy_level,
                    diff=build_diff_output.diff,
                    checks=check_results,
                    rolls=load_rolls(turn_dir / "rolls.yaml"),
                    interventions=intervention_file.interventions,
                )
                write_agent_io_component(
                    turn_dir,
                    "stop_conditions",
                    [
                        {
                            "name": item.name.value,
                            "should_stop": item.should_stop,
                            "log_only": item.log_only,
                        }
                        for item in stop_conditions
                    ],
                )
                if has_error or any(item.should_stop for item in stop_conditions):
                    status = TurnStatus.STOPPED_FOR_REVIEW
                    applied = False
                elif commit_mode == "auto":
                    apply_result = apply_state_diff(bundle, build_diff_output.diff)
                    StateStore.save(apply_result.bundle, paths.state)
                    status = TurnStatus.APPLIED
                    applied = True
                else:
                    status = TurnStatus.PENDING_REVIEW
                    applied = False
                write_state_diff(
                    turn_dir, build_diff_output.diff, build_diff_output.rejected_changes, applied
                )
                if status == TurnStatus.APPLIED and intervention_file.interventions:
                    history_entries = build_history_entries(
                        intervention_file.interventions, resolved_events, build_diff_output.diff
                    )
                    append_history(paths.root / "interventions.yaml", history_entries)
                if status == TurnStatus.APPLIED and project.user_mode == UserMode.GOD:
                    write_review_yaml(
                        turn_dir,
                        turn=turn,
                        decision="accept_all",
                        decided_by=project.user_mode,
                        resulting_turn_status=status,
                        auto_applied=True,
                    )
        except Exception as exc:  # noqa: BLE001 - must never swallow: recorded as `failed`
            status = TurnStatus.FAILED
            error = ErrorReport(
                phase=current_phase[0], exception_type=type(exc).__name__, message=str(exc)
            )
        finally:
            write_meta(
                turn_dir,
                build_meta_dict(
                    turn=turn,
                    status=status,
                    commit_mode=commit_mode,
                    phase_durations=durations,
                    calls=gateway.calls,
                    rng_draws_consumed=engine.draws_consumed - initial_rng_offset,
                    error=error,
                ),
            )

        return TurnRunResult(turn=turn, status=status, turn_dir=turn_dir)
