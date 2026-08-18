from __future__ import annotations

from living_narrative.book.benchmark import benchmark_book, write_book_benchmark_report
from living_narrative.workspace.init import create_project


def test_book_benchmark_writes_public_stable_report_without_workspace_path(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Benchmark")
    workspace = project_yaml.parent / "workspace"

    observation = benchmark_book(workspace, name="empty-book")
    report_path = write_book_benchmark_report(tmp_path / "report.json", [observation])
    report = report_path.read_text(encoding="utf-8")

    assert observation.planned_chapters == 0
    assert observation.accepted_chapters == 0
    assert len(observation.artifact_fingerprint) == 64
    assert '"schema_version": 1' in report
    assert str(workspace) not in report
    assert "prompt" not in report
