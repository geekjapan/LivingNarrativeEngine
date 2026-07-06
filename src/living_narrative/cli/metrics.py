"""``living-narrative metrics``: regression-quality metrics summary (docs/issues/019).

Human-readable by default (compact Japanese labels), full JSON with ``--json``. Thin wrapper
over ``session.metrics.collect_metrics`` — no aggregation logic lives here.
"""

from pathlib import Path

import typer

from living_narrative.cli._common import runtime_error, usage_error
from living_narrative.session.metrics import (
    EmotionMetrics,
    MetricsError,
    ProjectMetrics,
    collect_metrics,
)


def metrics(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    if not project.exists():
        usage_error(f"project not found: {project}")
    try:
        result = collect_metrics(project)
    except MetricsError as exc:
        runtime_error(str(exc))

    if json_output:
        typer.echo(result.model_dump_json())
        return

    typer.echo(_format_summary(result))


def _format_summary(result: ProjectMetrics) -> str:
    lines = [
        f"turns: {result.turns.total} (timeline={result.turns.timeline_entries}, "
        f"discarded={result.turns.discarded}, rolledback={result.turns.rolledback})",
        f"  status内訳: {result.turns.by_status}",
    ]

    lines.append("emotions:")
    for character in result.emotions:
        parts = [_format_emotion(e) for e in character.emotions]
        lines.append(f"  {character.character_id}: {', '.join(parts) if parts else '(なし)'}")

    lines.append(
        "pacing: "
        f"stall件数={result.pacing.stall_event_count}, "
        f"最長連続停滞={result.pacing.max_consecutive_stall_turns}"
    )
    lines.append(
        "threads: "
        f"open={result.threads.opened}, advance={result.threads.advanced}, "
        f"resolve={result.threads.resolved}, 最長放置ターン={result.threads.max_open_turns}"
    )

    lines.append("threats:")
    for threat in result.threats:
        lines.append(
            f"  {threat.threat_id}: pressure {threat.initial_pressure}→{threat.final_pressure}, "
            f"stage発火={threat.stage_fired_turns}"
        )

    lines.append(
        "scenes: "
        f"遷移={result.scenes.transition_count}, active数={result.scenes.final_active_count}, "
        f"active={result.scenes.final_active_scene_ids}"
    )
    lines.append(
        f"checks: by_source={result.checks.by_source}, by_severity={result.checks.by_severity}"
    )
    lines.append(f"memory: summary件数={result.memory.summary_count}")
    return "\n".join(lines)


def _format_emotion(emotion: EmotionMetrics) -> str:
    if emotion.min is None:
        return f"{emotion.emotion}=final:{emotion.final} (baseline未定義)"
    return (
        f"{emotion.emotion}=final:{emotion.final}/min:{emotion.min}/max:{emotion.max}"
        f"/天井連続:{emotion.max_consecutive_at_ceiling}"
    )
