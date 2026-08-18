"""Reader manuscript export from accepted immutable chapter attempts only."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml
from pydantic import BaseModel

from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.state.diff import fsync_directory
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore


class IncompleteManuscriptError(ValueError):
    """The requested BookPlan has a chapter without an accepted manuscript input."""


class ManuscriptExportResult(BaseModel):
    manuscript_path: Path
    manifest_path: Path
    chapter_count: int


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


def export_accepted_manuscript(workspace_root: Path, output_dir: Path) -> ManuscriptExportResult:
    """Write a reader-safe manuscript and manifest from BookPlan-ordered accepted attempts."""
    bundle = StateStore.load(workspace_root / "state")
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
        bodies.append(attempt.candidate_markdown)
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
    _atomic_write_text(manuscript_path, manuscript)
    _atomic_write_text(
        manifest_path,
        yaml.safe_dump(
            {
                "schema_version": 1,
                "manuscript_sha256": hashlib.sha256(manuscript.encode("utf-8")).hexdigest(),
                "chapters": manifest_chapters,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
    )
    return ManuscriptExportResult(
        manuscript_path=manuscript_path,
        manifest_path=manifest_path,
        chapter_count=len(manifest_chapters),
    )
