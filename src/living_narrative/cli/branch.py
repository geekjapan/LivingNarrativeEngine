"""``living-narrative branch``: copy a project and rewind the copy to an earlier turn,
leaving the original untouched (cli/spec.md; Issue 018)."""

from pathlib import Path

import typer

from living_narrative.cli._common import load_project_or_exit, usage_error
from living_narrative.session.rollback import (
    RollbackError,
    append_branch_title_suffix,
    copy_project_for_branch,
    execute_rollback,
    plan_rollback,
)
from living_narrative.workspace.loader import load_project


def branch(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    from_turn: int = typer.Option(..., "--from-turn", help="Turn number the branch starts at"),
    output: Path = typer.Option(..., "--output", help="Directory for the new branched project"),
) -> None:
    read = load_project_or_exit(project)

    try:
        plan = plan_rollback(read.paths.runs, from_turn)
    except RollbackError as exc:
        usage_error(str(exc))

    try:
        branch_project_path = copy_project_for_branch(project.parent, output)
    except RollbackError as exc:
        usage_error(str(exc))

    branch_read = load_project(branch_project_path)
    execute_rollback(branch_read.paths, plan)
    append_branch_title_suffix(branch_project_path, from_turn)

    typer.echo(f"branched at turn {from_turn}: {output}")
    typer.echo(f"state: {branch_read.paths.state}")
