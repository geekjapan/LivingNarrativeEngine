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

from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.cli._common import runtime_error, usage_error

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
