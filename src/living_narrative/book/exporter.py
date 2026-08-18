"""Reader manuscript export from accepted immutable chapter attempts only."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import yaml
from pydantic import BaseModel

from living_narrative.book.continuity import strip_chapter_scaffolding
from living_narrative.book.coordinator import resolve_workspace_dirs
from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.state.diff import fsync_directory
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import WorkspacePaths


class IncompleteManuscriptError(ValueError):
    """The requested BookPlan has a chapter without an accepted manuscript input."""


class ManuscriptExportResult(BaseModel):
    manuscript_path: Path
    manifest_path: Path
    chapter_count: int


def _publish_manuscript_generation(output_dir: Path, manuscript: str, manifest: str) -> None:
    """Stage manuscript artifacts and publish a generation marker last."""
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".manuscript_generation.", dir=output_dir))
    generation = yaml.safe_dump(
        {
            "schema_version": 1,
            "manuscript_sha256": hashlib.sha256(manuscript.encode("utf-8")).hexdigest(),
            "manifest_sha256": hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
        },
        allow_unicode=True,
        sort_keys=False,
    )
    try:
        _atomic_write_text(staging / "manuscript.md", manuscript)
        _atomic_write_text(staging / "manuscript_manifest.yaml", manifest)
        _atomic_write_text(staging / "manuscript_generation.yaml", generation)
        os.replace(staging / "manuscript.md", output_dir / "manuscript.md")
        os.replace(staging / "manuscript_manifest.yaml", output_dir / "manuscript_manifest.yaml")
        os.replace(
            staging / "manuscript_generation.yaml", output_dir / "manuscript_generation.yaml"
        )
        fsync_directory(output_dir)
    finally:
        for leftover in staging.glob("*"):
            leftover.unlink(missing_ok=True)
        staging.rmdir()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def export_accepted_manuscript(
    workspace: Path | WorkspacePaths, output_dir: Path
) -> ManuscriptExportResult:
    """Write a reader-safe manuscript and manifest from BookPlan-ordered accepted attempts.

    Accepts the resolved ``load_project()`` paths so a project whose ``workspace.state`` is not
    ``<root>/state`` exports from its own canonical state.
    """
    workspace_root, state_dir, _ = resolve_workspace_dirs(workspace)
    bundle = StateStore.load(state_dir)
    bodies: list[str] = []
    manifest_chapters: list[dict[str, str]] = []
    chapters_root = workspace_root / "books" / "chapters"
    for chapter in bundle.book_plan.chapters:
        ledger = bundle.book_ledger.chapter(chapter.id)
        if ledger.lifecycle is not ChapterLifecycle.ACCEPTED:
            raise IncompleteManuscriptError(f"chapter {chapter.id} is not accepted")
        lineage = load_chapter_lineage(chapters_root, chapter.id)
        if lineage.accepted_attempt_id is None:
            raise IncompleteManuscriptError(f"chapter {chapter.id} has no accepted attempt")
        attempt = next(
            (item for item in lineage.attempts if item.id == lineage.accepted_attempt_id), None
        )
        if attempt is None:
            raise IncompleteManuscriptError(f"accepted attempt is missing for {chapter.id}")
        # The manuscript is the reader artifact: the compile frontmatter, generated heading and
        # `> Planned goal:` author prompt are production scaffolding, never narration.
        bodies.append(strip_chapter_scaffolding(attempt.candidate_markdown))
        manifest_chapters.append(
            {
                "chapter_id": chapter.id,
                "attempt_id": attempt.id,
                "candidate_sha256": attempt.candidate_sha256,
            }
        )
    manuscript_path = output_dir / "manuscript.md"
    manifest_path = output_dir / "manuscript_manifest.yaml"
    manuscript = "\n\n".join(bodies)
    manifest = yaml.safe_dump(
        {
            "schema_version": 1,
            "manuscript_sha256": hashlib.sha256(manuscript.encode("utf-8")).hexdigest(),
            "chapters": manifest_chapters,
        },
        allow_unicode=True,
        sort_keys=False,
    )
    _publish_manuscript_generation(output_dir, manuscript, manifest)
    return ManuscriptExportResult(
        manuscript_path=manuscript_path,
        manifest_path=manifest_path,
        chapter_count=len(manifest_chapters),
    )
