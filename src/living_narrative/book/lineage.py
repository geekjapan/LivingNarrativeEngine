"""Immutable candidate attempts and accepted-attempt lineage for one chapter."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.review import ChapterReview, ChapterReviewDecision
from living_narrative.state.diff import fsync_directory


class ChapterAttempt(BaseModel):
    """One immutable candidate/review pair, loaded with its durable body artifact."""

    id: str = Field(pattern=r"^attempt_\d{3}$")
    chapter_id: str = Field(pattern=r"^chapter_\d+$")
    parent_attempt_id: str | None = Field(default=None, pattern=r"^attempt_\d{3}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_turns: list[int] = Field(default_factory=list)
    draft_run_id: str | None = None
    review: ChapterReview
    candidate_markdown: str = ""


class ChapterLineage(BaseModel):
    """The complete immutable history and the one accepted manuscript input."""

    chapter_id: str = Field(pattern=r"^chapter_\d+$")
    attempts: list[ChapterAttempt] = Field(default_factory=list)
    accepted_attempt_id: str | None = Field(default=None, pattern=r"^attempt_\d{3}$")


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


def _write_yaml(path: Path, payload: dict) -> None:
    _atomic_write_text(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def _manifest_path(chapters_root: Path, chapter_id: str) -> Path:
    return chapters_root / chapter_id / "lineage.yaml"


def _attempt_dir(chapters_root: Path, chapter_id: str, attempt_id: str) -> Path:
    return chapters_root / chapter_id / "attempts" / attempt_id


def _stored_attempt(attempt: ChapterAttempt) -> dict:
    return attempt.model_dump(mode="json", exclude={"candidate_markdown"})


def _stored_lineage(lineage: ChapterLineage) -> dict:
    return lineage.model_dump(
        mode="json",
        exclude={"attempts": {"__all__": {"candidate_markdown"}}},
    )


def _load_manifest(chapters_root: Path, chapter_id: str) -> ChapterLineage:
    path = _manifest_path(chapters_root, chapter_id)
    if not path.is_file():
        return ChapterLineage(chapter_id=chapter_id)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    lineage = ChapterLineage.model_validate(payload)
    if lineage.chapter_id != chapter_id:
        raise ValueError("chapter lineage id does not match requested chapter")
    attempts: list[ChapterAttempt] = []
    for attempt in lineage.attempts:
        body_path = _attempt_dir(chapters_root, chapter_id, attempt.id) / "candidate.md"
        if not body_path.is_file():
            raise ValueError(f"candidate artifact missing for {chapter_id}/{attempt.id}")
        markdown = body_path.read_text(encoding="utf-8")
        digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        if digest != attempt.candidate_sha256:
            raise ValueError(f"candidate artifact hash mismatch for {chapter_id}/{attempt.id}")
        attempts.append(attempt.model_copy(update={"candidate_markdown": markdown}))
    return lineage.model_copy(update={"attempts": attempts})


def load_chapter_lineage(chapters_root: Path, chapter_id: str) -> ChapterLineage:
    """Load and integrity-check all immutable attempts for one planned chapter."""
    return _load_manifest(chapters_root, chapter_id)


def record_chapter_attempt(
    chapters_root: Path,
    candidate: ChapterCandidate,
    review: ChapterReview,
    *,
    draft_run_id: str | None = None,
) -> ChapterAttempt:
    """Append one immutable candidate attempt and return the saved attempt."""
    if candidate.chapter_id != review.chapter_id:
        raise ValueError("candidate and review chapter_id must match")
    lineage = _load_manifest(chapters_root, candidate.chapter_id)
    candidate_sha256 = hashlib.sha256(candidate.markdown.encode("utf-8")).hexdigest()
    if any(attempt.candidate_sha256 == candidate_sha256 for attempt in lineage.attempts):
        raise FileExistsError("an immutable attempt already exists for this candidate body")

    attempt_id = f"attempt_{len(lineage.attempts) + 1:03d}"
    attempt = ChapterAttempt(
        id=attempt_id,
        chapter_id=candidate.chapter_id,
        parent_attempt_id=lineage.attempts[-1].id if lineage.attempts else None,
        candidate_sha256=candidate_sha256,
        source_turns=candidate.source_turns,
        draft_run_id=draft_run_id,
        review=review,
        candidate_markdown=candidate.markdown,
    )
    attempt_dir = _attempt_dir(chapters_root, candidate.chapter_id, attempt_id)
    if attempt_dir.exists():
        raise FileExistsError(f"attempt already exists: {attempt_dir}")
    _atomic_write_text(attempt_dir / "candidate.md", candidate.markdown)
    _write_yaml(attempt_dir / "review.yaml", review.model_dump(mode="json"))
    _write_yaml(attempt_dir / "attempt.yaml", _stored_attempt(attempt))
    updated = lineage.model_copy(update={"attempts": [*lineage.attempts, attempt]})
    _write_yaml(_manifest_path(chapters_root, candidate.chapter_id), _stored_lineage(updated))
    return attempt


def accept_chapter_attempt(chapters_root: Path, chapter_id: str, attempt_id: str) -> ChapterLineage:
    """Select an existing accept-reviewed attempt without changing its immutable files."""
    lineage = _load_manifest(chapters_root, chapter_id)
    attempt = next((item for item in lineage.attempts if item.id == attempt_id), None)
    if attempt is None:
        raise ValueError(f"attempt not found: {attempt_id}")
    if attempt.review.decision is not ChapterReviewDecision.ACCEPT:
        raise ValueError("cannot accept an attempt whose review decision is not accept")
    updated = lineage.model_copy(update={"accepted_attempt_id": attempt_id})
    _write_yaml(_manifest_path(chapters_root, chapter_id), _stored_lineage(updated))
    return updated
