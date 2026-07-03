"""``living-narrative export replay`` (export-replay/spec.md, cli/spec.md Impact)."""

from pathlib import Path

import typer

from living_narrative.cli._common import load_project_or_exit, runtime_error, usage_error
from living_narrative.export_replay import NoReplayableTurnsError, assemble_replay

app = typer.Typer(name="export", help="Export commands")


@app.command("replay")
def replay(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    output: Path = typer.Option(..., "--output", help="Destination replay.md path"),
    style: str = typer.Option("novel", "--style", help="novel|log"),
) -> None:
    if style not in ("novel", "log"):
        usage_error(f"unknown --style: {style!r} (expected 'novel' or 'log')")

    read = load_project_or_exit(project)
    try:
        content = assemble_replay(read.paths.runs, style=style)
    except NoReplayableTurnsError as exc:
        runtime_error(str(exc))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    typer.echo(f"Wrote {output}")
