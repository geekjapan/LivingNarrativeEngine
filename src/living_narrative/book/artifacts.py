"""Durable, reviewable chapter artifact persistence."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.review import ChapterReview
from living_narrative.state.diff import fsync_directory


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


def _atomic_write_yaml(path: Path, data: Any) -> None:
    _atomic_write_text(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def save_chapter_artifacts(
    chapters_root: Path,
    candidate: ChapterCandidate,
    review: ChapterReview,
) -> Path:
    """Persist one candidate and its review with independently atomic files."""
    if candidate.chapter_id != review.chapter_id:
        raise ValueError("candidate and review chapter_id must match")
    artifact_dir = chapters_root / candidate.chapter_id
    _atomic_write_text(artifact_dir / "candidate.md", candidate.markdown)
    _atomic_write_yaml(
        artifact_dir / "candidate.yaml",
        {"chapter_id": candidate.chapter_id, "source_turns": candidate.source_turns},
    )
    _atomic_write_yaml(artifact_dir / "review.yaml", review.model_dump(mode="json"))
    return artifact_dir


def load_chapter_artifacts(
    chapters_root: Path, chapter_id: str
) -> tuple[ChapterCandidate, ChapterReview]:
    """Load the complete candidate/review pair, failing fast on a partial artifact."""
    artifact_dir = chapters_root / chapter_id
    metadata = yaml.safe_load((artifact_dir / "candidate.yaml").read_text(encoding="utf-8")) or {}
    review_data = yaml.safe_load((artifact_dir / "review.yaml").read_text(encoding="utf-8")) or {}
    candidate = ChapterCandidate(
        chapter_id=metadata["chapter_id"],
        source_turns=metadata["source_turns"],
        markdown=(artifact_dir / "candidate.md").read_text(encoding="utf-8"),
    )
    return candidate, ChapterReview.model_validate(review_data)
