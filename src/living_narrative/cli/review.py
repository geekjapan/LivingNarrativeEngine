"""``living-narrative review``: resolve a pending/stopped-for-review turn (cli/spec.md
"review による pending diff のインタラクティブフロー")."""

import sys
from pathlib import Path

import typer
import yaml

from living_narrative.cli._common import echo_turn_result, load_project_or_exit, usage_error
from living_narrative.pipeline import TurnPipeline, TurnStatus, turn_dir_path
from living_narrative.session.rerun import rerun_rng_offset
from living_narrative.session.resume import restore_resume_state
from living_narrative.session.review import ReviewDecision, resolve_review


def _parse_apply_indices(raw: list[str]) -> set[int]:
    indices: set[int] = set()
    for item in raw:
        for piece in item.split(","):
            piece = piece.strip()
            if not piece:
                continue
            try:
                indices.add(int(piece))
            except ValueError:
                usage_error(f"--apply must be integer indices, got: {piece!r}")
    return indices


def _prompt_decision() -> ReviewDecision:
    value = typer.prompt("decision", type=typer.Choice([item.value for item in ReviewDecision]))
    return ReviewDecision(value)


def review(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    decision: ReviewDecision | None = typer.Option(
        None, "--decision", help="accept_all|reject_all|partial|edit|rerun_turn"
    ),
    apply_: list[str] = typer.Option(
        [], "--apply", help="0-based change indices for --decision partial, comma-separated"
    ),
    patch: Path | None = typer.Option(
        None, "--patch", help="Edited state diff YAML file for --decision edit"
    ),
    replay_same_seed: bool = typer.Option(
        False, "--replay-same-seed", help="Only valid with --decision rerun_turn"
    ),
) -> None:
    if replay_same_seed and decision is not None and decision != ReviewDecision.RERUN_TURN:
        usage_error("--replay-same-seed requires --decision rerun_turn")

    read = load_project_or_exit(project)
    resume_state = restore_resume_state(read.paths.runs, read.paths.root / "interventions.yaml")
    pending_turn = resume_state.pending_review_turn
    if pending_turn is None:
        typer.echo("レビュー対象のターンはありません")
        return

    if decision is None:
        if not sys.stdin.isatty():
            usage_error("--decision is required (no TTY available for an interactive prompt)")
        decision = _prompt_decision()
        if replay_same_seed and decision != ReviewDecision.RERUN_TURN:
            usage_error("--replay-same-seed requires --decision rerun_turn")

    if decision == ReviewDecision.PARTIAL and not apply_:
        usage_error("--decision partial requires --apply")
    if decision == ReviewDecision.EDIT and patch is None:
        usage_error("--decision edit requires --patch")

    turn_dir = turn_dir_path(read.paths.runs, pending_turn)
    selected_indices = _parse_apply_indices(apply_) if decision == ReviewDecision.PARTIAL else None
    edited_diff = None
    if decision == ReviewDecision.EDIT:
        edited_diff = yaml.safe_load(patch.read_text(encoding="utf-8"))

    result = resolve_review(
        workspace_root=read.paths.root,
        state_dir=read.paths.state,
        turn_dir=turn_dir,
        decision=decision,
        decided_by=read.config.user_mode,
        selected_change_indices=selected_indices,
        edited_diff=edited_diff,
    )

    if decision != ReviewDecision.RERUN_TURN:
        typer.echo(f"turn {pending_turn}: {decision.value} -> {result.resulting_turn_status}")
        return

    offset = rerun_rng_offset(read.paths.runs, pending_turn, replay_same_seed=replay_same_seed)
    rerun_result = TurnPipeline().run(project, rng_offset_override=offset)
    echo_turn_result(rerun_result.turn_dir, rerun_result.turn, rerun_result.status.value)
    if rerun_result.status == TurnStatus.FAILED:
        raise typer.Exit(code=1)
