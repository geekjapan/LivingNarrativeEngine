"""``living-narrative export`` (export-replay/spec.md, cli/spec.md Impact)."""

from pathlib import Path

import typer
import yaml

from living_narrative.cli._common import load_project_or_exit, runtime_error, usage_error
from living_narrative.export_replay import (
    NoReplayableTurnsError,
    ReconstructionError,
    assemble_replay,
    reconstruct_session,
    render_scenes_markdown,
)

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


@app.command("scenes")
def scenes(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    gm: bool = typer.Option(False, "--gm", help="Include gm_only key events (e.g. thread_update)"),
) -> None:
    read = load_project_or_exit(project)
    try:
        reconstruction = reconstruct_session(project, include_gm=gm)
    except ReconstructionError as exc:
        runtime_error(str(exc))

    output_dir = read.paths.exports
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml_path = output_dir / "scenes.yaml"
    yaml_path.write_text(
        yaml.safe_dump(reconstruction.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    markdown_path = output_dir / "scenes.md"
    markdown_path.write_text(render_scenes_markdown(reconstruction), encoding="utf-8")

    typer.echo(f"Wrote {yaml_path}")
    typer.echo(f"Wrote {markdown_path}")
