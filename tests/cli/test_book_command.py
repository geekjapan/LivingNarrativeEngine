from __future__ import annotations

import yaml
from typer.testing import CliRunner

from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
    plan_generation,
    start_chapter_production,
)
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_runner import (
    ChapterProductionRunner,
    ChapterProductionRunStatus,
    ProductionRunPhase,
)
from living_narrative.cli import app
from living_narrative.cli import book as book_module
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project

runner = CliRunner()


class _Gateway:
    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        if binding_key == "chapter_draft":
            return response_schema(
                body="澪は駅の時刻表に刻まれた矛盾を見つけ、改札の外へ駆け出した。"
            )
        if binding_key == "chapter_continuity":
            return response_schema(required_threads_covered=[], findings=[])
        raise AssertionError(f"unexpected binding: {binding_key}")


def _production_project(tmp_path):
    project_yaml = create_project(tmp_path / "production-book", title="Production Book")
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "霧の駅から帰還する。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "異常を知る。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "時刻表の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml


def _running_production_run(project_yaml):
    workspace = project_yaml.parent / "workspace"
    start_chapter_production(workspace, "chapter_001")
    bundle = StateStore.load(workspace / "state")
    run_id = f"generation_{plan_generation(bundle)}_revision_001"
    run_dir = workspace / "runs" / "chapter_production" / "chapter_001" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "request.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "run_id": run_id, "chapter_id": "chapter_001"}),
        encoding="utf-8",
    )
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "run_id": run_id,
                "chapter_id": "chapter_001",
                "phase": "drafting",
            }
        ),
        encoding="utf-8",
    )
    return run_dir


def _story_bible() -> dict[str, object]:
    return {
        "premise": "霧の駅からの帰還を描く。",
        "audience": "長編ミステリ読者",
        "language": "ja",
        "acts": [
            {
                "id": "act_001",
                "promise": "閉じ込められた理由を提示する。",
                "chapter_ids": ["chapter_001"],
            }
        ],
        "chapters": [
            {
                "id": "chapter_001",
                "act_id": "act_001",
                "planned_goal": "時刻表の矛盾を発見する。",
                "required_thread_ids": ["thread_001"],
                "character_arc_targets": [],
                "target_word_range": {"min_words": 2500, "max_words": 4500},
            }
        ],
    }


def test_book_plan_writes_reviewable_structured_proposal(tmp_path):
    bible_path = tmp_path / "story-bible.yaml"
    output_path = tmp_path / "book-plan-proposal.yaml"
    bible_path.write_text(yaml.safe_dump(_story_bible(), allow_unicode=True), encoding="utf-8")

    result = runner.invoke(
        app,
        ["book", "plan", "--story-bible", str(bible_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0, result.output
    proposal = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert proposal["proposal_id"].startswith("book_plan_")
    assert proposal["book_plan"]["chapters"][0]["id"] == "chapter_001"
    assert proposal["book_ledger"]["active_chapter_id"] == "chapter_001"
    assert "canonical state was not changed" in result.output


def test_book_plan_rejects_invalid_story_bible(tmp_path):
    bible_path = tmp_path / "invalid-story-bible.yaml"
    bible_path.write_text("premise: ''\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["book", "plan", "--story-bible", str(bible_path), "--output", str(tmp_path / "out.yaml")],
    )

    assert result.exit_code == 2
    assert "story bible" in result.output


def test_book_chapter_run_status_outputs_a_durable_reader_safe_projection(tmp_path):
    project_yaml = _production_project(tmp_path)
    ChapterProductionRunner().run(project_yaml, "chapter_001", gateway=_Gateway())

    result = runner.invoke(
        app,
        [
            "book",
            "chapter-run-status",
            "--project",
            str(project_yaml),
            "--chapter",
            "chapter_001",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = yaml.safe_load(result.output)
    assert payload["phase"] == "awaiting_author"
    assert payload["lifecycle"] == "review"
    assert payload["attempt_id"] == "attempt_001"
    assert "prompt" not in payload
    assert "credential" not in payload


def test_book_stop_chapter_run_records_a_durable_stop_request(tmp_path):
    project_yaml = _production_project(tmp_path)
    run_dir = _running_production_run(project_yaml)

    result = runner.invoke(
        app,
        [
            "book",
            "stop-chapter-run",
            "--project",
            str(project_yaml),
            "--chapter",
            "chapter_001",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = yaml.safe_load(result.output)
    assert payload["phase"] == "drafting"
    assert payload["lifecycle"] == "running"
    assert payload["stopped_reason"] == "author_requested"
    request = yaml.safe_load((run_dir / "stop_requested.yaml").read_text(encoding="utf-8"))
    assert request["reason"] == "author_requested"


def test_book_run_chapter_delegates_to_the_domain_runner_and_returns_public_status(
    tmp_path, monkeypatch
):
    project_yaml = _production_project(tmp_path)
    observed: dict[str, object] = {}

    def fake_run(self, project, chapter, *, gateway=None, budget=None):
        observed["project"] = project
        observed["chapter"] = chapter
        return ChapterProductionRunStatus(
            run_id="generation_example_revision_001",
            chapter_id=chapter,
            phase=ProductionRunPhase.AWAITING_AUTHOR,
            lifecycle=ChapterLifecycle.REVIEW,
            draft_run_id="chapter_chapter_001_example_attempt_001",
            attempt_id="attempt_001",
        )

    monkeypatch.setattr(book_module.ChapterProductionRunner, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "book",
            "run-chapter",
            "--project",
            str(project_yaml),
            "--chapter",
            "chapter_001",
        ],
    )

    assert result.exit_code == 0, result.output
    assert observed == {"project": project_yaml, "chapter": "chapter_001"}
    payload = yaml.safe_load(result.output)
    assert payload["phase"] == "awaiting_author"
    assert payload["lifecycle"] == "review"
    assert "auto_accept" not in payload


def test_book_benchmark_writes_a_reader_safe_read_only_report(tmp_path):
    project_yaml = _production_project(tmp_path)
    output_path = tmp_path / "benchmark.json"
    before = StateStore.load(project_yaml.parent / "workspace" / "state").model_dump(mode="json")

    result = runner.invoke(
        app,
        [
            "book",
            "benchmark",
            "--project",
            str(project_yaml),
            "--name",
            "one-chapter",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    report = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 3
    assert len(report["books"]) == 1
    book = report["books"][0]
    assert book["name"] == "one-chapter"
    assert book["planned_chapters"] == 1
    assert book["accepted_chapters"] == 0
    assert book["revising_chapters"] == 0
    assert book["blocked_chapters"] == 0
    assert book["attempt_count"] == 0
    assert book["open_thread_count"] == 0
    assert book["production_run_count"] == 0
    assert book["failed_production_run_count"] == 0
    assert len(book["artifact_fingerprint"]) == 64
    assert len(book["production_run_fingerprint"]) == 64
    assert "benchmark report:" in result.output
    assert str(project_yaml.parent) not in output_path.read_text(encoding="utf-8")
    after = StateStore.load(project_yaml.parent / "workspace" / "state").model_dump(mode="json")
    assert after == before


def test_book_benchmark_returns_runtime_error_when_expected_fingerprint_differs(tmp_path):
    project_yaml = _production_project(tmp_path)
    output_path = tmp_path / "benchmark.json"

    result = runner.invoke(
        app,
        [
            "book",
            "benchmark",
            "--project",
            str(project_yaml),
            "--name",
            "one-chapter",
            "--output",
            str(output_path),
            "--expect-fingerprint",
            "0" * 64,
        ],
    )

    assert result.exit_code == 1
    assert "benchmark fingerprint differs" in result.output
    assert output_path.is_file()


def test_book_benchmark_accepts_an_explicit_duration_slo(tmp_path):
    project_yaml = _production_project(tmp_path)
    output_path = tmp_path / "benchmark.json"

    result = runner.invoke(
        app,
        [
            "book",
            "benchmark",
            "--project",
            str(project_yaml),
            "--name",
            "one-chapter-slo",
            "--output",
            str(output_path),
            "--max-duration-ms",
            "10000",
        ],
    )

    assert result.exit_code == 0, result.output
    report = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert report["books"][0]["duration_ms"] >= 0
    assert report["duration_slo"]["max_duration_ms"] == 10_000
    assert report["duration_slo"]["evaluations"][0]["within_budget"] is True
    rendered = yaml.safe_dump(report, allow_unicode=True)
    assert "prompt" not in rendered


def test_book_benchmark_writes_report_before_a_duration_slo_failure(tmp_path, monkeypatch):
    project_yaml = _production_project(tmp_path)
    output_path = tmp_path / "benchmark.json"
    original_benchmark = book_module.benchmark_book

    def slow_benchmark(workspace, *, name):
        return original_benchmark(workspace, name=name).model_copy(update={"duration_ms": 1})

    monkeypatch.setattr(book_module, "benchmark_book", slow_benchmark)

    result = runner.invoke(
        app,
        [
            "book",
            "benchmark",
            "--project",
            str(project_yaml),
            "--name",
            "one-chapter-slo-failure",
            "--output",
            str(output_path),
            "--max-duration-ms",
            "0",
        ],
    )

    assert result.exit_code == 1
    assert "benchmark duration exceeded: expected <= 0ms, observed 1ms" in result.output
    report = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 3
    assert report["books"][0]["duration_ms"] == 1


def test_book_benchmark_rejects_an_invalid_project_as_usage_error(tmp_path):
    project_yaml = tmp_path / "invalid" / "project.yaml"
    project_yaml.parent.mkdir()
    project_yaml.write_text("title: incomplete\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "book",
            "benchmark",
            "--project",
            str(project_yaml),
            "--name",
            "invalid",
            "--output",
            str(tmp_path / "report.json"),
        ],
    )

    assert result.exit_code == 2
    assert "invalid project" in result.output


def test_book_publication_export_and_verify_commands_use_accepted_manuscript(tmp_path):
    project_yaml = _production_project(tmp_path)
    ChapterProductionRunner().run(project_yaml, "chapter_001", gateway=_Gateway())
    accept_chapter_review(project_yaml.parent / "workspace", "chapter_001")
    output_dir = tmp_path / "publication"

    exported = runner.invoke(
        app,
        [
            "book",
            "export-publication",
            "--project",
            str(project_yaml),
            "--output",
            str(output_dir),
        ],
    )

    assert exported.exit_code == 0, exported.output
    manifest_path = output_dir / "publication_manifest.yaml"
    assert manifest_path.is_file()
    assert (output_dir / "manuscript.docx").is_file()
    assert (output_dir / "manuscript.epub").is_file()
    assert (output_dir / "manuscript.pdf").is_file()

    verified = runner.invoke(
        app,
        ["book", "verify-publication", "--manifest", str(manifest_path)],
    )

    assert verified.exit_code == 0, verified.output
    payload = yaml.safe_load(verified.output)
    assert payload["format_names"] == ["docx", "epub", "pdf"]
    assert "公開本文" not in verified.output
    assert "prompt" not in verified.output
    assert "credential" not in verified.output
