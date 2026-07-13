"""``living-narrative rollback``: rewind project state to an earlier applied turn using
each turn's saved inverse diff (cli/spec.md; Issue 018)."""

from pathlib import Path

import typer

from living_narrative.cli._common import load_project_or_exit, runtime_error, usage_error
from living_narrative.session.rollback import RollbackError, execute_rollback, plan_rollback
from living_narrative.state.transaction import RecoveryError


def rollback(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    to_turn: int = typer.Option(..., "--to-turn", help="Turn number to roll back to"),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt"),
) -> None:
    read = load_project_or_exit(project)
    try:
        plan = plan_rollback(read.paths.runs, to_turn)
    except RollbackError as exc:
        usage_error(str(exc))

    if not yes:
        turns = ", ".join(str(turn) for turn in plan.rolled_back_turns)
        confirmed = typer.confirm(
            f"Roll back turn(s) {turns} (turn {plan.current_turn} -> turn {plan.to_turn})?"
        )
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    try:
        result = execute_rollback(read.paths, plan)
    except RecoveryError as exc:
        runtime_error(str(exc))
    turns = ", ".join(str(turn) for turn in result.rolled_back_turns)
    typer.echo(f"rolled back turn(s): {turns}")
    typer.echo(f"now at turn {result.to_turn}")
    typer.echo(f"state: {read.paths.state}")
