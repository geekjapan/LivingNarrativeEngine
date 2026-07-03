"""``living-narrative turn``: run one turn (cli/spec.md "turn による単一ターン実行" and friends)."""

import contextlib
from pathlib import Path

import typer
import yaml

from living_narrative.cli._common import echo_turn_result, load_project_or_exit, usage_error
from living_narrative.cli._intervention_flags import DEFAULT_VISIBILITY, TYPE_TARGET_KIND
from living_narrative.intervention.schema import InterventionType
from living_narrative.pipeline import LoadError, TurnPipeline, TurnStatus, UnresolvedTurnError
from living_narrative.state.models import UserMode, Visibility


@contextlib.contextmanager
def _optional_user_mode_override(project_path: Path, mode: UserMode | None):
    """``--as <mode>``: patch ``user_mode`` on disk for the run, then restore verbatim."""
    if mode is None:
        yield
        return
    original = project_path.read_text(encoding="utf-8")
    data = yaml.safe_load(original) or {}
    data["user_mode"] = mode.value
    project_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    try:
        yield
    finally:
        project_path.write_text(original, encoding="utf-8")


def _parse_constraints(raw: list[str]) -> dict[str, str]:
    constraints: dict[str, str] = {}
    for item in raw:
        key, sep, value = item.partition("=")
        if not sep:
            usage_error(f"--constraint must be key=value, got: {item!r}")
        constraints[key] = value
    return constraints


def turn(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    intervention: str | None = typer.Option(
        None, "--intervention", help="Free-text intervention (via the Interpreter)"
    ),
    type_: InterventionType | None = typer.Option(
        None, "--type", help="Direct-input intervention type (no LLM interpretation)"
    ),
    target: str | None = typer.Option(None, "--target", help="Target id, e.g. char_002"),
    content: str | None = typer.Option(None, "--content", help="Intervention content"),
    visibility: Visibility | None = typer.Option(
        None, "--visibility", help="Overrides the type's default visibility"
    ),
    constraint: list[str] = typer.Option([], "--constraint", help="key=value, repeatable"),
    as_mode: UserMode | None = typer.Option(
        None, "--as", help="Temporarily override user_mode for this turn only"
    ),
) -> None:
    if intervention is not None and type_ is not None:
        usage_error("--intervention and --type cannot be specified together")
    if type_ is None and (target is not None or content is not None or constraint or visibility):
        usage_error("--target/--content/--visibility/--constraint require --type")
    if type_ is not None and content is None:
        usage_error("--type requires --content")
    if as_mode is UserMode.PLAYER_CHARACTER:
        usage_error("--as player_character is not supported (requires a session char_id binding)")

    load_project_or_exit(project)

    direct_drafts = None
    if type_ is not None:
        draft: dict[str, object] = {
            "type": type_.value,
            "target": {"kind": TYPE_TARGET_KIND[type_], **({"id": target} if target else {})},
            "content": content,
            "constraints": _parse_constraints(constraint),
            "visibility": (visibility or DEFAULT_VISIBILITY[type_]).value,
        }
        direct_drafts = [draft]

    pipeline = TurnPipeline()
    try:
        with _optional_user_mode_override(project, as_mode):
            result = pipeline.run(
                project,
                intervention_text=intervention,
                intervention_drafts=direct_drafts,
            )
    except UnresolvedTurnError as exc:
        usage_error(f"{exc} — resolve it first with `living-narrative review --project {project}`")
    except LoadError as exc:
        usage_error(str(exc))

    echo_turn_result(result.turn_dir, result.turn, result.status.value)
    if result.status == TurnStatus.FAILED:
        raise typer.Exit(code=1)
