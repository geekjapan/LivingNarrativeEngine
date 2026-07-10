"""Validated project backup and restore operations."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from living_narrative.workspace.copy import (
    copy_directory_atomic,
    copy_directory_into,
    paths_overlap,
    publish_directory_atomic,
)
from living_narrative.workspace.loader import load_project


class BackupError(ValueError):
    """A backup or restore request is invalid or unsafe."""


class BackupManifest(BaseModel):
    """Portable metadata stored at the root of every project backup."""

    model_config = ConfigDict(extra="forbid")

    source_path: Path
    created_at: datetime
    schema_version: int

    @field_validator("source_path")
    @classmethod
    def source_path_must_be_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("source_path must be absolute")
        return value

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must be timezone-aware UTC")
        return value


def _project_error(project_path: Path) -> str:
    read = load_project(project_path)
    details = [f"{issue.field}: {issue.message}" for issue in read.errors]
    details.extend(f"missing state file: {name}" for name in read.missing_state_files)
    return "; ".join(details) or "invalid project"


def create_backup(
    project_path: Path,
    output_parent: Path,
    *,
    created_at: datetime | None = None,
) -> Path:
    """Create a manifest plus a complete project copy under ``output_parent``."""
    project_path = project_path.resolve()
    source_root = project_path.parent
    output_parent = output_parent.resolve()
    if paths_overlap(source_root, output_parent):
        raise BackupError("backup source and output must not contain one another")

    read = load_project(project_path)
    if not read.is_valid or read.config is None:
        raise BackupError(_project_error(project_path))

    timestamp = created_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise BackupError("backup timestamp must be timezone-aware")
    timestamp = timestamp.astimezone(UTC)
    project_name = re.sub(r"[^A-Za-z0-9._-]+", "-", read.config.id).strip("-.") or "project"
    backup_name = f"{project_name}-backup-{timestamp.strftime('%Y%m%dT%H%M%SZ')}"
    backup_root = output_parent / backup_name
    if backup_root.exists():
        raise BackupError(f"backup destination already exists: {backup_root}")

    manifest = BackupManifest(
        source_path=source_root,
        created_at=timestamp,
        schema_version=read.config.schema_version,
    )

    def populate(temporary: Path) -> None:
        (temporary / "project").mkdir()
        copy_directory_into(source_root, temporary / "project")
        (temporary / "manifest.yaml").write_text(
            yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )

    return publish_directory_atomic(backup_root, populate)


def load_backup_manifest(backup_root: Path) -> BackupManifest:
    """Load and validate a backup manifest and its required project layout."""
    backup_root = backup_root.resolve()
    manifest_path = backup_root / "manifest.yaml"
    project_path = backup_root / "project" / "project.yaml"
    if not manifest_path.is_file():
        raise BackupError(f"backup manifest is missing: {manifest_path}")
    if not project_path.is_file():
        raise BackupError(f"backup project is missing: {project_path}")
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest = BackupManifest.model_validate(raw)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        raise BackupError(f"invalid backup manifest: {exc}") from exc
    return manifest


def restore_backup(backup_root: Path, output_dir: Path) -> BackupManifest:
    """Validate and atomically restore a backup's project directory."""
    backup_root = backup_root.resolve()
    output_dir = output_dir.resolve()
    if paths_overlap(backup_root, output_dir):
        raise BackupError("restore backup and output must not contain one another")
    manifest = load_backup_manifest(backup_root)
    project_path = backup_root / "project" / "project.yaml"
    read = load_project(project_path)
    if not read.is_valid or read.config is None:
        raise BackupError(f"invalid backup project: {_project_error(project_path)}")
    if manifest.schema_version != read.config.schema_version:
        raise BackupError(
            "backup manifest schema_version does not match project schema_version: "
            f"{manifest.schema_version} != {read.config.schema_version}"
        )
    restore_empty_output = output_dir.exists()
    if restore_empty_output:
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise BackupError(f"restore output is not an empty directory: {output_dir}")
        output_dir.rmdir()
    try:
        copy_directory_atomic(backup_root / "project", output_dir)
    except BaseException:
        if restore_empty_output and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        raise
    return manifest


__all__ = [
    "BackupError",
    "BackupManifest",
    "create_backup",
    "load_backup_manifest",
    "restore_backup",
]
