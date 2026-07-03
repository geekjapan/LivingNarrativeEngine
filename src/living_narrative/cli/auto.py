"""``living-narrative auto``: multi-turn autonomous progression (cli/spec.md "auto による複数
ターン自動進行" and "auto --until scene_end")."""

from pathlib import Path

import typer
import yaml

from living_narrative.cli._common import echo_turn_result, load_project_or_exit, usage_error
from living_narrative.pipeline import LoadError, TurnStatus, UnresolvedTurnError
from living_narrative.session.loop import run_auto_loop

# ponytail: no engine primitive stops "exactly at scene_end and nothing else" — the
# pipeline's own stop-condition evaluation (which always includes scene_end) already
# halts the loop long before this; it's just a safety net against a world that never
# ends its scene.
_UNTIL_SCENE_END_TURN_CAP = 500


def auto(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    turns: int | None = typer.Option(None, "--turns", help="Run at most N turns"),
    until: str | None = typer.Option(
        None, "--until", help="Run until this condition (only 'scene_end' is supported)"
    ),
) -> None:
    if turns is not None and until is not None:
        usage_error("--turns and --until cannot be specified together")
    if turns is None and until is None:
        usage_error("either --turns or --until is required")
    if until is not None and until != "scene_end":
        usage_error(f"unsupported --until value: {until!r} (only 'scene_end' is supported)")

    load_project_or_exit(project)
    target_turn_count = turns if turns is not None else _UNTIL_SCENE_END_TURN_CAP

    try:
        loop_result = run_auto_loop(project, target_turn_count)
    except UnresolvedTurnError as exc:
        usage_error(f"{exc} — resolve it first with `living-narrative review --project {project}`")
    except LoadError as exc:
        usage_error(str(exc))

    for run_result in loop_result.turns:
        echo_turn_result(run_result.turn_dir, run_result.turn, run_result.status.value)
        if run_result.status != TurnStatus.APPLIED:
            reasons = _stop_reasons(run_result.turn_dir)
            if reasons:
                typer.echo(f"stopped: {', '.join(reasons)}")

    hit_cap = loop_result.turns and len(loop_result.turns) >= _UNTIL_SCENE_END_TURN_CAP
    if until is not None and hit_cap:
        typer.echo(
            f"warning: reached the {_UNTIL_SCENE_END_TURN_CAP}-turn safety cap "
            "without the scene ending",
            err=True,
        )

    last = loop_result.turns[-1] if loop_result.turns else None
    if last is not None and last.status == TurnStatus.FAILED:
        raise typer.Exit(code=1)


def _stop_reasons(turn_dir: Path) -> list[str]:
    path = turn_dir / "agent_io" / "stop_conditions.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [item["name"] for item in data if item.get("should_stop")]
