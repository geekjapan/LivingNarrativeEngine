"""Reader-safe, rebuildable artifact index for long-form Book workspaces.

The index is a performance artifact only.  Benchmark reads remain the source of
truth, so a missing index can always be rebuilt and an invalid index fails closed.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from living_narrative.book.benchmark import benchmark_book
from living_narrative.book.coordinator import resolve_workspace_dirs
from living_narrative.state.diff import fsync_directory


class BookArtifactIndex(BaseModel):
    """Path-free fingerprints and aggregate counts safe to persist for lookup."""

    schema_version: int = 1
    planned_chapters: int = Field(ge=0)
    artifact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_run_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def _index_path(workspace: Path) -> Path:
    _, _, runs_dir = resolve_workspace_dirs(workspace)
    return runs_dir / "book_artifact_index" / "index.yaml"


def load_book_artifact_index(workspace: Path) -> BookArtifactIndex | None:
    """Load a valid reader-safe index, or return ``None`` when no index exists."""
    path = _index_path(workspace)
    if not path.is_file():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return BookArtifactIndex.model_validate(payload)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError("book artifact index is invalid") from exc


def ensure_book_artifact_index(workspace: Path) -> BookArtifactIndex:
    """Return the valid cache or rebuild it from authoritative artifacts when absent."""
    return load_book_artifact_index(workspace) or build_book_artifact_index(workspace)


def build_book_artifact_index(workspace: Path) -> BookArtifactIndex:
    """Rebuild the index from authoritative artifacts and atomically publish it."""
    observation = benchmark_book(workspace, name="artifact-index")
    index = BookArtifactIndex(
        planned_chapters=observation.planned_chapters,
        artifact_fingerprint=observation.artifact_fingerprint,
        production_run_fingerprint=observation.production_run_fingerprint,
        benchmark_fingerprint=observation.benchmark_fingerprint,
    )
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
