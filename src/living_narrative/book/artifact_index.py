"""Reader-safe, rebuildable artifact index for long-form Book workspaces.

The index is a performance artifact only.  Benchmark reads remain the source of
truth, so a missing index can always be rebuilt and an invalid index fails closed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from living_narrative.book.benchmark import benchmark_book
from living_narrative.book.coordinator import resolve_workspace_dirs
from living_narrative.state.diff import fsync_directory
from living_narrative.workspace.loader import WorkspacePaths


class BookArtifactIndex(BaseModel):
    """Path-free fingerprints and aggregate counts safe to persist for lookup."""

    schema_version: int = 2
    planned_chapters: int = Field(ge=0)
    accepted_chapter_count: int = Field(ge=0)
    lineage_attempt_count: int = Field(ge=0)
    production_run_count: int = Field(ge=0)
    publication_format_count: int = Field(ge=0)
    artifact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    lineage_metadata_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_run_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_metadata_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    publication_manifest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    publication_metadata_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    benchmark_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _verify_integrity(self) -> BookArtifactIndex:
        payload = self.model_dump(mode="json", exclude={"index_sha256"})
        if self.index_sha256 != _canonical_sha256(payload):
            raise ValueError("book artifact index integrity mismatch")
        return self


def _canonical_sha256(payload: object) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _publication_metadata(
    workspace: Path | WorkspacePaths,
) -> tuple[int, str | None, str | None]:
    exports_dir = (
        workspace.exports if isinstance(workspace, WorkspacePaths) else workspace / "exports"
    )
    manifest_path = exports_dir / "publication_manifest.yaml"
    if not manifest_path.is_file():
        return 0, None, None
    try:
        raw_manifest = manifest_path.read_bytes()
        manifest = yaml.safe_load(raw_manifest) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError("publication manifest is invalid") from exc
    if not isinstance(manifest, dict):
        raise ValueError("publication manifest is invalid")
    formats = manifest.get("formats", {})
    if not isinstance(formats, dict):
        raise ValueError("publication manifest is invalid")
    safe_formats = {
        str(name): {
            "filename": value.get("filename"),
            "sha256": value.get("sha256"),
        }
        for name, value in formats.items()
        if isinstance(value, dict)
    }
    metadata = {
        "schema_version": manifest.get("schema_version"),
        "manuscript_sha256": manifest.get("manuscript_sha256"),
        "source_manuscript_manifest_sha256": manifest.get("source_manuscript_manifest_sha256"),
        "quality_gate": manifest.get("quality_gate"),
        "license": manifest.get("license"),
        "formats": safe_formats,
    }
    return (
        len(safe_formats),
        hashlib.sha256(raw_manifest).hexdigest(),
        _canonical_sha256(metadata),
    )


def _index_path(workspace: Path | WorkspacePaths) -> Path:
    _, _, runs_dir = resolve_workspace_dirs(workspace)
    return runs_dir / "book_artifact_index" / "index.yaml"


def load_book_artifact_index(workspace: Path | WorkspacePaths) -> BookArtifactIndex | None:
    """Load a valid reader-safe index, or return ``None`` when no index exists."""
    path = _index_path(workspace)
    if not path.is_file():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return BookArtifactIndex.model_validate(payload)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError("book artifact index is invalid") from exc


def ensure_book_artifact_index(workspace: Path | WorkspacePaths) -> BookArtifactIndex:
    """Return the valid cache or rebuild it from authoritative artifacts when absent or invalid."""
    try:
        existing = load_book_artifact_index(workspace)
    except ValueError:
        existing = None
    return existing or build_book_artifact_index(workspace)


def build_book_artifact_index(workspace: Path | WorkspacePaths) -> BookArtifactIndex:
    """Rebuild the index from authoritative artifacts and atomically publish it."""
    observation = benchmark_book(workspace, name="artifact-index")
    (
        publication_format_count,
        publication_manifest_sha256,
        publication_metadata_fingerprint,
    ) = _publication_metadata(workspace)
    payload = {
        "schema_version": 2,
        "planned_chapters": observation.planned_chapters,
        "accepted_chapter_count": observation.accepted_chapters,
        "lineage_attempt_count": observation.attempt_count,
        "production_run_count": observation.production_run_count,
        "publication_format_count": publication_format_count,
        "publication_manifest_sha256": publication_manifest_sha256,
        "artifact_fingerprint": observation.artifact_fingerprint,
        "lineage_metadata_fingerprint": observation.artifact_fingerprint,
        "production_run_fingerprint": observation.production_run_fingerprint,
        "run_metadata_fingerprint": observation.production_run_fingerprint,
        "publication_metadata_fingerprint": publication_metadata_fingerprint,
        "benchmark_fingerprint": observation.benchmark_fingerprint,
    }
    index = BookArtifactIndex(**payload, index_sha256=_canonical_sha256(payload))
    path = _index_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            yaml.safe_dump(
                index.model_dump(mode="json"),
                stream,
                allow_unicode=True,
                sort_keys=False,
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return index


__all__ = [
    "BookArtifactIndex",
    "build_book_artifact_index",
    "ensure_book_artifact_index",
    "load_book_artifact_index",
]
