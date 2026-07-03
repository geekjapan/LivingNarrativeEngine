"""``living-narrative`` typer app. Later changes register more subcommands here."""

from pathlib import Path

import typer

from living_narrative.workspace.init import InitDestinationExistsError, create_project

app = typer.Typer(name="living-narrative")


@app.command()
def init(
    output: Path = typer.Argument(..., help="Destination directory for the new project"),
    title: str = typer.Option(..., "--title", help="Project title"),
) -> None:
    """Create a new project with a minimal empty-world workspace."""
    try:
        project_path = create_project(output, title)
    except InitDestinationExistsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Created project at {project_path}")


if __name__ == "__main__":
    app()
