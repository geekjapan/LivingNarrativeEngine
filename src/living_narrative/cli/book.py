"""Long-form planning commands.

The initial command deliberately writes a review artifact only.  It never mutates
canonical state: an accepted proposal is converted to an explicit StateDiff by
the book coordinator in a later workflow step.
"""

from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError

from living_narrative.book.benchmark import benchmark_book, write_book_benchmark_report
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_runner import (
    ChapterProductionRunner,
    ChapterProductionRunStatus,
)
from living_narrative.cli._common import load_project_or_exit, runtime_error, usage_error

app = typer.Typer(name="book", help="Long-form book planning commands")


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        runtime_error(f"could not read story bible {path}: {exc}")
    except yaml.YAMLError as exc:
        usage_error(f"invalid story bible YAML: {exc}")


@app.command("plan")
def plan(
    story_bible: Annotated[
        Path,
        typer.Option(..., "--story-bible", help="Path to a structured story-bible YAML file"),
    ],
    output: Annotated[
        Path,
        typer.Option(..., "--output", help="Path for the reviewable book-plan proposal YAML"),
    ],
) -> None:
    """Validate a Story Bible and write a deterministic, non-mutating proposal."""
    if not story_bible.exists():
        usage_error(f"story bible not found: {story_bible}")
    try:
        bible = StoryBible.model_validate(_read_yaml(story_bible))
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        usage_error(f"invalid story bible: {details}")

    proposal = build_book_plan_proposal(bible)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(proposal.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    typer.echo(f"book plan proposal: {output}")
    typer.echo("canonical state was not changed; review the proposal before applying its StateDiff")


@app.command("benchmark")
def benchmark(
    project: Annotated[Path, typer.Option(..., "--project", help="Path to project.yaml")],
    name: Annotated[str, typer.Option(..., "--name", help="Stable benchmark fixture name")],
    output: Annotated[Path, typer.Option(..., "--output", help="Path for the public JSON report")],
    expected_fingerprint: Annotated[
        str | None,
        typer.Option(
            "--expect-fingerprint",
            help="Expected combined benchmark fingerprint; mismatch exits with code 1",
        ),
    ] = None,
) -> None:
    """Write a read-only, reader-safe Book benchmark report for one project."""
    read = load_project_or_exit(project)
    if read.paths is None:
        runtime_error(f"project paths unavailable: {project}")
    try:
        observation = benchmark_book(read.paths, name=name)
        report_path = write_book_benchmark_report(output, [observation])
    except (OSError, ValueError) as exc:
        runtime_error(str(exc))
    fingerprint_differs = (
        expected_fingerprint is not None
        and expected_fingerprint != observation.benchmark_fingerprint
    )
    if fingerprint_differs:
        runtime_error(
            "benchmark fingerprint differs: "
            f"expected {expected_fingerprint}, observed {observation.benchmark_fingerprint}"
        )
    typer.echo(f"benchmark report: {report_path}")


def _echo_production_run_status(status: ChapterProductionRunStatus) -> None:
    """Emit only the runner's public status projection."""
    typer.echo(yaml.safe_dump(status.model_dump(mode="json"), allow_unicode=True, sort_keys=False))


@app.command("run-chapter")
def run_chapter(
    project: Annotated[Path, typer.Option(..., "--project", help="Path to project.yaml")],
    chapter: Annotated[str, typer.Option(..., "--chapter", help="Chapter ID to produce")],
) -> None:
    """Synchronously start or resume one chapter production run."""
    if not project.exists():
        usage_error(f"project not found: {project}")
    try:
        status = ChapterProductionRunner().run(project, chapter)
    except ValueError as exc:
        runtime_error(str(exc))
    _echo_production_run_status(status)


@app.command("chapter-run-status")
def chapter_run_status(
    project: Annotated[Path, typer.Option(..., "--project", help="Path to project.yaml")],
    chapter: Annotated[str, typer.Option(..., "--chapter", help="Chapter ID to inspect")],
) -> None:
    """Read the durable status of one chapter production run."""
    if not project.exists():
        usage_error(f"project not found: {project}")
    try:
        status = ChapterProductionRunner().status(project, chapter)
    except ValueError as exc:
        runtime_error(str(exc))
    _echo_production_run_status(status)


@app.command("stop-chapter-run")
def stop_chapter_run(
    project: Annotated[Path, typer.Option(..., "--project", help="Path to project.yaml")],
    chapter: Annotated[str, typer.Option(..., "--chapter", help="Chapter ID to stop")],
) -> None:
    """Request a safe phase-boundary stop for one chapter production run."""
    if not project.exists():
        usage_error(f"project not found: {project}")
    try:
        status = ChapterProductionRunner().request_stop(project, chapter)
    except ValueError as exc:
        runtime_error(str(exc))
    _echo_production_run_status(status)
