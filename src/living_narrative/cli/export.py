"""``living-narrative export`` (export-replay/spec.md, cli/spec.md Impact)."""

from pathlib import Path

import typer
import yaml

from living_narrative.cli._common import load_project_or_exit, runtime_error, usage_error
from living_narrative.export_replay import (
    DEFAULT_PROFILE,
    ArcsError,
    NoReplayableTurnsError,
    ReconstructionError,
    assemble_replay,
    build_arcs_report,
    build_outline,
    narration_by_turn_from_records,
    reconstruct_session,
    render_arcs_markdown,
    render_novel,
    render_outline_markdown,
    render_scenes_markdown,
    render_trpg_replay,
)
from living_narrative.export_replay.loader import load_turn_records
from living_narrative.pipeline.llm_gateway import LLMGateway

app = typer.Typer(name="export", help="Export commands")

_NO_TURNS_MESSAGE = "no applied (non-reject_all) turn exists yet — run `turn`/`auto` first"


@app.command("replay")
def replay(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    output: Path = typer.Option(..., "--output", help="Destination replay.md path"),
    style: str = typer.Option("novel", "--style", help="novel|log"),
    trpg: bool = typer.Option(
        False,
        "--trpg",
        help="GM-facing TRPG-style output (rolls/interventions/scene headings); ignores --style",
    ),
) -> None:
    if not trpg and style not in ("novel", "log"):
        usage_error(f"unknown --style: {style!r} (expected 'novel' or 'log')")

    read = load_project_or_exit(project)
    try:
        if trpg:
            reconstruction = reconstruct_session(project, include_gm=True)
            records = load_turn_records(read.paths.runs)
            content = render_trpg_replay(records, reconstruction)
        else:
            content = assemble_replay(read.paths.runs, style=style)
    except (NoReplayableTurnsError, ReconstructionError) as exc:
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


@app.command("outline")
def outline(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
) -> None:
    """LLM-free: derive a chapter outline (outline.yaml/outline.md) from the run so far."""
    read = load_project_or_exit(project)
    try:
        reconstruction = reconstruct_session(project)
    except ReconstructionError as exc:
        runtime_error(str(exc))

    records = load_turn_records(read.paths.runs)
    if not any(record.is_body_turn for record in records):
        runtime_error(_NO_TURNS_MESSAGE)

    result = build_outline(reconstruction, narration_by_turn_from_records(records))

    output_dir = read.paths.exports
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml_path = output_dir / "outline.yaml"
    yaml_path.write_text(
        yaml.safe_dump(result.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    markdown_path = output_dir / "outline.md"
    markdown_path.write_text(render_outline_markdown(result), encoding="utf-8")

    typer.echo(f"Wrote {yaml_path}")
    typer.echo(f"Wrote {markdown_path}")


@app.command("novel")
def novel(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    profile: str = typer.Option(
        DEFAULT_PROFILE, "--profile", help="LLM binding key used for the per-chapter prose pass"
    ),
) -> None:
    """LLM pass: derive a chapter outline, then rewrite it into novel_draft.md."""
    read = load_project_or_exit(project)
    try:
        reconstruction = reconstruct_session(project)
    except ReconstructionError as exc:
        runtime_error(str(exc))

    records = load_turn_records(read.paths.runs)
    if not any(record.is_body_turn for record in records):
        runtime_error(_NO_TURNS_MESSAGE)

    result = build_outline(reconstruction, narration_by_turn_from_records(records))

    gateway = LLMGateway(project=read.config, random_seed=read.config.random_seed)
    content = render_novel(read.config, result, gateway, profile=profile)

    output_dir = read.paths.exports
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "novel_draft.md"
    output_path.write_text(content, encoding="utf-8")

    typer.echo(f"Wrote {output_path}")


@app.command("arcs")
def arcs(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
) -> None:
    """LLM-free: character emotion/relationship arcs + thread/memory summary report (GM向け)."""
    read = load_project_or_exit(project)
    try:
        report = build_arcs_report(project)
    except ArcsError as exc:
        runtime_error(str(exc))

    output_dir = read.paths.exports
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml_path = output_dir / "arcs.yaml"
    yaml_path.write_text(
        yaml.safe_dump(report.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    markdown_path = output_dir / "arcs.md"
    markdown_path.write_text(render_arcs_markdown(report), encoding="utf-8")

    typer.echo(f"Wrote {yaml_path}")
    typer.echo(f"Wrote {markdown_path}")
