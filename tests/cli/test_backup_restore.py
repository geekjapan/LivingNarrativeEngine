"""Backup/restore CLI and filesystem safety regression tests (Issue 047)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from living_narrative.cli import app
from living_narrative.workspace import copy as copy_module
from living_narrative.workspace.backup import BackupError, create_backup, restore_backup

runner = CliRunner()


def test_backup_and_restore_round_trip_with_manifest(tmp_path, build_project):
    project_path = build_project(tmp_path / "source", title="Backup Test")
    extra = project_path.parent / "notes.txt"
    extra.write_text("keep me", encoding="utf-8")
    backups = tmp_path / "backups"

    backup_result = runner.invoke(
        app, ["backup", "--project", str(project_path), "--output", str(backups)]
    )

    assert backup_result.exit_code == 0, backup_result.output
    backup_root = next(backups.iterdir())
    assert backup_root.name.startswith("backup-test-backup-")
    manifest = yaml.safe_load((backup_root / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["source_path"] == str(project_path.parent.resolve())
    assert datetime.fromisoformat(manifest["created_at"]).tzinfo is not None
    assert manifest["schema_version"] == 1
    assert (backup_root / "project" / "notes.txt").read_text(encoding="utf-8") == "keep me"

    restored = tmp_path / "restored"
    restore_result = runner.invoke(app, ["restore", str(backup_root), "--output", str(restored)])
    assert restore_result.exit_code == 0, restore_result.output
    assert "schema_version: 1" in restore_result.output
    assert (restored / "project.yaml").is_file()
    assert (restored / "notes.txt").read_text(encoding="utf-8") == "keep me"


def test_backup_refuses_timestamp_collision(tmp_path, build_project):
    project_path = build_project(tmp_path / "source")
    created_at = datetime(2026, 7, 11, 12, 30, tzinfo=UTC)
    output = tmp_path / "backups"
    create_backup(project_path, output, created_at=created_at)

    with pytest.raises(BackupError, match="already exists"):
        create_backup(project_path, output, created_at=created_at)


def test_restore_allows_existing_empty_directory(tmp_path, build_project):
    project_path = build_project(tmp_path / "source")
    backup_root = create_backup(project_path, tmp_path / "backups")
    output = tmp_path / "restored"
    output.mkdir()

    restore_backup(backup_root, output)

    assert (output / "project.yaml").is_file()


def test_restore_refuses_non_empty_directory(tmp_path, build_project):
    project_path = build_project(tmp_path / "source")
    backup_root = create_backup(project_path, tmp_path / "backups")
    output = tmp_path / "restored"
    output.mkdir()
    marker = output / "do-not-overwrite.txt"
    marker.write_text("original", encoding="utf-8")

    result = runner.invoke(app, ["restore", str(backup_root), "--output", str(output)])

    assert result.exit_code == 2
    assert marker.read_text(encoding="utf-8") == "original"


@pytest.mark.parametrize("manifest", [None, "not: [valid"])
def test_restore_rejects_missing_or_invalid_manifest(tmp_path, manifest):
    backup_root = tmp_path / "backup"
    (backup_root / "project").mkdir(parents=True)
    (backup_root / "project" / "project.yaml").write_text("title: x\n", encoding="utf-8")
    if manifest is not None:
        (backup_root / "manifest.yaml").write_text(manifest, encoding="utf-8")

    result = runner.invoke(
        app, ["restore", str(backup_root), "--output", str(tmp_path / "restored")]
    )

    assert result.exit_code == 2
    assert "manifest" in result.output


def test_restore_rejects_missing_or_invalid_project(tmp_path, build_project):
    project_path = build_project(tmp_path / "source")
    backup_root = create_backup(project_path, tmp_path / "backups")
    (backup_root / "project" / "project.yaml").unlink()

    missing = runner.invoke(
        app, ["restore", str(backup_root), "--output", str(tmp_path / "missing")]
    )
    assert missing.exit_code == 2
    assert "project is missing" in missing.output

    backup_root = create_backup(project_path, tmp_path / "other-backups")
    (backup_root / "project" / "project.yaml").write_text("not: a project\n", encoding="utf-8")
    invalid = runner.invoke(
        app, ["restore", str(backup_root), "--output", str(tmp_path / "invalid")]
    )
    assert invalid.exit_code == 2
    assert "invalid backup project" in invalid.output


def test_restore_rejects_manifest_project_schema_mismatch(tmp_path, build_project):
    project_path = build_project(tmp_path / "source")
    backup_root = create_backup(project_path, tmp_path / "backups")
    manifest_path = backup_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 2
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    result = runner.invoke(
        app, ["restore", str(backup_root), "--output", str(tmp_path / "restored")]
    )

    assert result.exit_code == 2
    assert "does not match" in result.output


def test_backup_and_restore_reject_recursive_path_relationships(tmp_path, build_project):
    project_path = build_project(tmp_path / "source")
    backup_result = runner.invoke(
        app,
        [
            "backup",
            "--project",
            str(project_path),
            "--output",
            str(project_path.parent / "backups"),
        ],
    )
    assert backup_result.exit_code == 2
    assert "contain" in backup_result.output

    backup_root = create_backup(project_path, tmp_path / "backups")
    restore_result = runner.invoke(
        app,
        ["restore", str(backup_root), "--output", str(backup_root / "restored")],
    )
    assert restore_result.exit_code == 2
    assert "contain" in restore_result.output


def test_backup_copy_failure_leaves_no_partial_destination(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path / "source")
    output = tmp_path / "backups"

    def fail_copytree(source: Path, destination: Path, *, dirs_exist_ok: bool) -> None:
        (destination / "partial.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated copy failure")

    monkeypatch.setattr(copy_module.shutil, "copytree", fail_copytree)

    with pytest.raises(OSError, match="simulated"):
        create_backup(project_path, output)

    assert list(output.iterdir()) == []


def test_restore_copy_failure_leaves_no_partial_destination(tmp_path, build_project, monkeypatch):
    project_path = build_project(tmp_path / "source")
    backup_root = create_backup(project_path, tmp_path / "backups")
    output = tmp_path / "restored"

    def fail_copytree(source: Path, destination: Path, *, dirs_exist_ok: bool) -> None:
        (destination / "partial.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated restore failure")

    monkeypatch.setattr(copy_module.shutil, "copytree", fail_copytree)

    with pytest.raises(OSError, match="simulated"):
        restore_backup(backup_root, output)

    assert not output.exists()
    assert not list(tmp_path.glob(".restored.tmp-*"))
