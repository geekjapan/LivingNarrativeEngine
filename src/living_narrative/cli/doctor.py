"""``living-narrative doctor``: inspect and safely repair turn recovery state."""

import json
from pathlib import Path
from typing import Any

import typer

from living_narrative.cli._common import load_project_or_exit, runtime_error
from living_narrative.state.transaction import (
    ProjectLockError,
    RecoveryError,
    RecoveryState,
    _apply_recovery_state,
    classify_recovery_state,
    latest_turn_directory,
    project_lock,
)


def _restore_command(backup_root: Path | None) -> str:
    source = str(backup_root) if backup_root is not None else "<backup-root>"
    return f"living-narrative restore {source} --output <new-project-directory>"


def _diagnose(project_root: Path, state_dir: Path, runs_dir: Path) -> dict[str, Any]:
    turn_dir = latest_turn_directory(runs_dir)
    state = classify_recovery_state(turn_dir, state_dir, apply=False)
    report: dict[str, Any] = {
        "state": state.value,
        "recovery_state": state.value,
        "turn": turn_dir.name if turn_dir is not None else None,
        "turn_dir": str(turn_dir) if turn_dir is not None else None,
        "state_dir": str(state_dir),
        "project_root": str(project_root),
    }
    if state is RecoveryState.QUARANTINE:
        report["action"] = (
            "quarantine cannot be cleared safely; restore a backup or manually repair "
            "state, then rerun doctor"
        )
        report["restore_command"] = _restore_command(None)
    elif state is RecoveryState.BLOCKED:
        report["action"] = "resolve the incomplete pre-beta turn manually before retrying"
    elif state is RecoveryState.RECOVER_META:
        report["action"] = "safe metadata completion is available with doctor --repair"
    elif state is RecoveryState.DISCARD:
        report["action"] = "safe turn discard is available with doctor --repair"
    else:
        report["action"] = "no recovery action required"
    return report


def doctor(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    repair: bool = typer.Option(
        False,
        "--repair",
        "--fix",
        help="Apply only hash-safe metadata completion or turn discard",
    ),
    backup: Path | None = typer.Option(
        None,
        "--backup",
        "--restore-from",
        help="Backup root to include in restore guidance",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    read = load_project_or_exit(project)
    if repair:
        try:
            with project_lock(read.paths.root):
                turn_dir = latest_turn_directory(read.paths.runs)
                before_report = _diagnose(read.paths.root, read.paths.state, read.paths.runs)
                state = RecoveryState(before_report["state"])
                if state in {RecoveryState.QUARANTINE, RecoveryState.BLOCKED}:
                    raise RecoveryError(
                        f"cannot repair project while recovery state is {state.value}",
                        target="doctor",
                        quarantine=state is RecoveryState.QUARANTINE,
                    )
                applied = _apply_recovery_state(turn_dir, state) if turn_dir is not None else False
                action = (
                    "completed meta.yaml"
                    if state is RecoveryState.RECOVER_META and applied
                    else "discarded incomplete turn"
                    if state is RecoveryState.DISCARD and applied
                    else "no action needed (legacy applied turn preserved)"
                    if state is RecoveryState.DISCARD
                    else "no changes"
                )
                report = _diagnose(read.paths.root, read.paths.state, read.paths.runs)
                for field in ("turn", "turn_dir"):
                    if before_report[field] is not None:
                        report[field] = before_report[field]
                report["action"] = action
        except (ProjectLockError, RecoveryError, OSError) as exc:
            runtime_error(str(exc))
    else:
        report = _diagnose(read.paths.root, read.paths.state, read.paths.runs)

    if backup is not None and report["state"] in {
        RecoveryState.QUARANTINE.value,
        RecoveryState.BLOCKED.value,
    }:
        report["restore_command"] = _restore_command(backup)

    if json_output:
        typer.echo(json.dumps(report, ensure_ascii=False))
        return

    typer.echo(f"recovery: {report['state']}")
    if report["turn"] is not None:
        typer.echo(f"turn: {report['turn']}")
    typer.echo(f"action: {report['action']}")
    if "restore_command" in report:
        typer.echo(f"restore guidance: {report['restore_command']}")


__all__ = ["doctor"]
