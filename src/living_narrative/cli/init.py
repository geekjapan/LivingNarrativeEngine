"""``living-narrative init``: full ``--genre``/``--tone``/``--template``/``--output`` contract
(project-workspace/spec.md MODIFIED Requirement "init コマンドによるプロジェクト作成")."""

from pathlib import Path

import typer

from living_narrative.cli._common import usage_error
from living_narrative.templates.registry import TEMPLATE_NAMES
from living_narrative.workspace.init import (
    InitDestinationExistsError,
    UnknownTemplateError,
    create_project,
)


def init(
    title: str = typer.Option(..., "--title", help="Project title"),
    output: Path = typer.Option(..., "--output", help="Destination directory for the new project"),
    genre: str = typer.Option("", "--genre", help="Project genre"),
    tone: str = typer.Option("", "--tone", help="Project tone"),
    template: str = typer.Option(
        "minimal", "--template", help=f"One of: {', '.join(TEMPLATE_NAMES)}"
    ),
) -> None:
    """Create a new project + workspace from ``--template`` (default: ``minimal``)."""
    try:
        project_path = create_project(output, title, genre=genre, tone=tone, template=template)
    except UnknownTemplateError as exc:
        usage_error(str(exc))
    except InitDestinationExistsError as exc:
        usage_error(str(exc))

    typer.echo(f"Created project at {project_path}")
