"""Thin CLI adapters for project backup and restore."""

from pathlib import Path

import typer

from living_narrative.cli._common import usage_error
from living_narrative.workspace.backup import BackupError, create_backup, restore_backup


def backup(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    output: Path = typer.Option(..., "--output", help="Parent directory for the backup"),
) -> None:
    try:
        backup_root = create_backup(project, output)
    except (BackupError, OSError) as exc:
        usage_error(str(exc))
    typer.echo(f"backup created: {backup_root}")


def restore(
    backup_root: Path = typer.Argument(..., help="Backup root containing manifest.yaml"),
    output: Path = typer.Option(..., "--output", help="Directory for the restored project"),
) -> None:
    try:
        manifest = restore_backup(backup_root, output)
    except (BackupError, OSError) as exc:
        usage_error(str(exc))
    typer.echo(f"restored: {output}")
    typer.echo(f"schema_version: {manifest.schema_version}")


__all__ = ["backup", "restore"]
