from __future__ import annotations

import ast

from living_narrative.book.coordinator import (
    accept_chapter_review,
    apply_book_plan_proposal,
)
from living_narrative.book.exporter import export_accepted_manuscript
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.production_runner import ChapterProductionRunner, ProductionRunPhase
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project


class _ScaleGateway:
    def __init__(
        self,
        runner: ChapterProductionRunner | None = None,
        stop_chapter_id: str | None = None,
    ):
        self.runner = runner
        self.stop_chapter_id = stop_chapter_id
        self.project_yaml = None
        self.stopped = False
        self.binding_keys: list[str] = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.binding_keys.append(binding_key)
        prompt = messages[1]["content"]
        if binding_key == "chapter_draft":
            chapter_id = prompt.split("Chapter: ", 1)[1].split("\n", 1)[0]
            if (
                self.runner is not None
                and self.project_yaml is not None
                and chapter_id == self.stop_chapter_id
                and not self.stopped
            ):
                self.runner.request_stop(self.project_yaml, chapter_id)
                self.stopped = True
            body = f"澪は{chapter_id}で時刻表の矛盾を観察し、次の手掛かりを残した。"
            return response_schema(body=body)
        if binding_key == "chapter_continuity":
            raw_threads = prompt.split("Required threads: ", 1)[1].split("\n", 1)[0]
            required_threads = ast.literal_eval(raw_threads)
            return response_schema(required_threads_covered=required_threads, findings=[])
        raise AssertionError(f"unexpected binding: {binding_key}")


def _scale_project(tmp_path, chapter_count: int = 20):
    project_yaml = create_project(tmp_path / "book", title="Scale Book")
    chapters = [
        {
            "id": f"chapter_{index:03d}",
            "act_id": "act_001" if index <= chapter_count // 2 else "act_002",
            "planned_goal": f"第{index}章で時刻表の矛盾を調べる。",
            "required_thread_ids": [f"thread_{index:03d}"],
            "target_word_range": {"min_words": 10, "max_words": 100},
        }
        for index in range(1, chapter_count + 1)
    ]
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "霧の駅から帰還する。",
                "audience": "fantasy readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "最初の異常を発見する。",
                        "chapter_ids": [
                            chapter["id"] for chapter in chapters[: chapter_count // 2]
                        ],
                    },
                    {
                        "id": "act_002",
                        "promise": "異常の原因へ近づく。",
                        "chapter_ids": [
                            chapter["id"] for chapter in chapters[chapter_count // 2 :]
                        ],
                    },
                ],
                "chapters": chapters,
            }
        )
    )
    apply_book_plan_proposal(project_yaml.parent / "workspace", proposal)
    return project_yaml


def test_twenty_chapter_quality_scale_e2e_covers_gate_resume_and_export(tmp_path):
    project_yaml = _scale_project(tmp_path)
    workspace = project_yaml.parent / "workspace"
    runner = ChapterProductionRunner()
    stopping_gateway = _ScaleGateway(runner, stop_chapter_id="chapter_010")
    stopping_gateway.project_yaml = project_yaml

    for index in range(1, 21):
        chapter_id = f"chapter_{index:03d}"
        status = runner.run(project_yaml, chapter_id, gateway=stopping_gateway)
        if chapter_id == "chapter_010":
            assert status.phase is ProductionRunPhase.STOPPED
            assert status.lifecycle is ChapterLifecycle.RUNNING
            resumed = runner.run(project_yaml, chapter_id, gateway=_ScaleGateway())
            assert resumed.phase is ProductionRunPhase.AWAITING_AUTHOR
            assert resumed.resumed is True
            status = resumed
        assert status.phase is ProductionRunPhase.AWAITING_AUTHOR
        assert status.lifecycle is ChapterLifecycle.REVIEW
        accept_chapter_review(workspace, chapter_id)

    result = export_accepted_manuscript(workspace, workspace / "exports" / "scale")
    bundle = StateStore.load(workspace / "state")

    assert result.chapter_count == 20
    assert result.manuscript_path.read_text(encoding="utf-8").count("時刻表の矛盾") == 20
    assert all(
        chapter.lifecycle is ChapterLifecycle.ACCEPTED for chapter in bundle.book_ledger.chapters
    )
    assert len(bundle.book_ledger.continuity.entries) == 20
    assert [summary.act_id for summary in bundle.book_ledger.continuity.act_summaries] == [
        "act_001",
        "act_002",
    ]
    assert bundle.book_ledger.continuity.open_thread_ids == []
