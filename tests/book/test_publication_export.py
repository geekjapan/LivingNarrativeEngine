from __future__ import annotations

import hashlib
import zipfile

import pytest
import yaml
from docx import Document
from pypdf import PdfReader

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
    open_chapter_review,
    record_chapter_candidate,
    start_chapter_production,
)
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.publication import (
    PublicationVerificationError,
    export_publication,
    verify_publication,
)
from living_narrative.book.review import ChapterReview, ChapterReviewDecision, ChapterReviewMetrics
from living_narrative.workspace.init import create_project


def _workspace(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "帳簿を調べる。",
                "audience": "fantasy readers",
                "acts": [{"id": "act_001", "promise": "調査", "chapter_ids": ["chapter_001"]}],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "矛盾を見つける。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter_001\n\n公開本文。\n",
    )
    review = ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.ACCEPT,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
    )
    workspace = project_yaml.parent / "workspace"
    start_chapter_production(workspace, "chapter_001")
    record_chapter_candidate(workspace, candidate, review)
    open_chapter_review(workspace, "chapter_001")
    accept_chapter_review(workspace, "chapter_001")
    return workspace


def test_publication_export_writes_hash_linked_docx_epub_pdf_and_manifest(tmp_path):
    workspace = _workspace(tmp_path)

    result = export_publication(workspace, tmp_path / "publication")

    assert set(result.format_paths) == {"docx", "epub", "pdf"}
    assert result.format_paths["docx"].read_bytes().startswith(b"PK")
    assert result.format_paths["epub"].read_bytes().startswith(b"PK")
    assert result.format_paths["pdf"].read_bytes().startswith(b"%PDF")
    assert "公開本文。" in "\n".join(
        paragraph.text for paragraph in Document(result.format_paths["docx"]).paragraphs
    )
    with zipfile.ZipFile(result.format_paths["epub"]) as archive:
        epub_text = b"".join(
            archive.read(name) for name in archive.namelist() if name.endswith(".xhtml")
        ).decode("utf-8")
    assert "公開本文。" in epub_text
    assert "公開本文。" in "\n".join(
        page.extract_text() or "" for page in PdfReader(result.format_paths["pdf"]).pages
    )
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    manuscript = (tmp_path / "publication" / "manuscript.md").read_bytes()
    assert manifest["schema_version"] == 1
    assert manifest["manuscript_sha256"] == hashlib.sha256(manuscript).hexdigest()
    assert set(manifest["formats"]) == {"docx", "epub", "pdf"}
    for name, path in result.format_paths.items():
        assert manifest["formats"][name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert manifest["formats"][name]["filename"] == path.name

    verified = verify_publication(result.manifest_path)
    assert verified.manuscript_sha256 == manifest["manuscript_sha256"]

    result.format_paths["docx"].write_bytes(b"tampered")
    with pytest.raises(PublicationVerificationError, match="sha256 mismatch"):
        verify_publication(result.manifest_path)
