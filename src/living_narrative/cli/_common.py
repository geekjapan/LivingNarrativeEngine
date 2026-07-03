"""Shared exit-code contract and project loading (cli/spec.md Requirement
"非対話フラグの網羅性とexit code契約"): 0 success, 1 runtime error, 2 input validation error.
"""

from pathlib import Path
from typing import NoReturn

import typer

from living_narrative.workspace.loader import ProjectReadResult, load_project


def echo_error(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)


def usage_error(message: str) -> NoReturn:
    """Exit 2: bad arguments/input (cli/spec.md exit code contract)."""
    echo_error(message)
    raise typer.Exit(code=2)


def runtime_error(message: str) -> NoReturn:
    """Exit 1: execution-time failure (turn failed, provider error, etc.)."""
    echo_error(message)
    raise typer.Exit(code=1)


def load_project_or_exit(project_path: Path) -> ProjectReadResult:
    if not project_path.exists():
        usage_error(f"project not found: {project_path}")
    result = load_project(project_path)
    if not result.is_valid:
        if result.errors:
            details = "; ".join(f"{issue.field}: {issue.message}" for issue in result.errors)
            usage_error(f"invalid project at {project_path}: {details}")
        state_dir = result.paths.state if result.paths else project_path
        usage_error(
            f"missing required state files under {state_dir}: "
            f"{', '.join(result.missing_state_files)}"
        )
    return result


def read_narration_body(narration_path: Path) -> str | None:
    """Strip ``write_narration``'s YAML frontmatter, returning just the prose/log body.

    Returns ``None`` if the turn failed before the Narrate phase ever ran (no
    ``narration.md`` was written) — ``failed`` is a legitimate turn outcome, not a CLI bug.
    """
    if not narration_path.exists():
        return None
    text = narration_path.read_text(encoding="utf-8")
    _, _, body = text.partition("---\n\n")
    return body.rstrip("\n")


def echo_turn_result(turn_dir: Path, turn: int, status: str) -> None:
    """Print a turn's narration (if any) and its status line — shared by turn/auto/review."""
    body = read_narration_body(turn_dir / "narration.md")
    if body is not None:
        typer.echo(body)
    typer.echo(f"turn {turn}: {status}")
