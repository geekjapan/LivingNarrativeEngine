"""Recoverable, provenance-rich LLM runs that draft one planned chapter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel

from living_narrative.book.budget import (
    BookBudgetPolicy,
    BudgetExceededError,
    evaluate_draft_budget,
)
from living_narrative.book.chapters import ChapterContext, build_chapter_context
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.state.diff import fsync_directory
from living_narrative.state.store import StateStore
from living_narrative.state.transaction import project_lock
from living_narrative.workspace.loader import load_project


class ChapterDraftResponse(BaseModel):
    """The only model-produced payload persisted by a chapter drafting run."""

    body: str


class _Gateway(Protocol):
    def complete(
        self,
        binding_key: str,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel],
        prompt_template_name: str,
    ) -> BaseModel: ...


@dataclass(frozen=True)
class ChapterDraftResult:
    run_id: str
    run_dir: Path
    response: ChapterDraftResponse
    resumed: bool


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


def _atomic_write_yaml(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def _load_response(path: Path) -> ChapterDraftResponse:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ChapterDraftResponse.model_validate(payload)


def _prompt(context: ChapterContext) -> list[dict[str, Any]]:
    reader_facts = "\n".join(f"- {fact}" for fact in context.reader_facts) or "- None"
    required_threads = "\n".join(f"- {thread_id}" for thread_id in context.required_thread_ids)
    required_threads = required_threads or "- None"
    return [
        {
            "role": "system",
            "content": (
                "Write original Japanese literary fiction. Preserve reader-visible facts only. "
                "Return the draft body only through the structured response."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Chapter: {context.chapter_id}\n"
                f"Act: {context.act_id}\n"
                f"Planned goal: {context.planned_goal}\n"
                f"Required threads:\n{required_threads}\n"
                f"Target body units: {context.target_min_words}-{context.target_max_words}\n"
                f"Reader-visible facts:\n{reader_facts}\n"
                f"Continuity summary:\n{context.memory_summary or 'None'}\n"
                f"Book continuity digest:\n{context.continuity_digest or 'None'}\n"
                "Write one self-contained chapter draft. Do not reveal GM-only or private facts."
            ),
        },
    ]


def run_chapter_draft(
    project_yaml: Path,
    chapter_id: str,
    *,
    attempt: int = 1,
    gateway: _Gateway | None = None,
    budget: BookBudgetPolicy | None = None,
) -> ChapterDraftResult:
    """Create or resume one recoverable chapter draft run.

    ``request.yaml`` and ``prompt.yaml`` are durable before a provider is called. A response is
    reusable after a process crash even when ``meta.yaml`` has not yet been written; the latter is
    always the final completion marker. Attempts are immutable run identities, allowing revision
    requests to retain their own provenance.
    """
    if attempt < 1:
        raise ValueError("attempt must be at least 1")
    read = load_project(project_yaml)
    if not read.is_valid or read.config is None or read.paths is None:
        raise ValueError(f"invalid project: {project_yaml}")

    workspace_root = read.paths.root
    state_dir = read.paths.state
    run_id = f"chapter_{chapter_id}_attempt_{attempt:03d}"
    drafts_root = read.paths.runs / "chapter_drafts"
    run_dir = drafts_root / run_id
    response_path = run_dir / "response.yaml"
    completion_path = run_dir / "meta.yaml"

    # The state snapshot is taken inside the lock: a context built beforehand can observe a
    # partially published transaction, or feed a superseded plan to the provider.
    with project_lock(workspace_root):
        bundle = StateStore.load(state_dir)
        context = build_chapter_context(bundle, chapter_id, source_turns=[])
        if completion_path.is_file() or response_path.is_file():
            response = _load_response(response_path)
            if not completion_path.is_file():
                _atomic_write_yaml(
                    completion_path,
                    {"status": "completed", "resumed_without_provider": True},
                )
            return ChapterDraftResult(run_id, run_dir, response, resumed=True)

        messages = _prompt(context)
        if budget is not None:
            stop_reason = evaluate_draft_budget(
                drafts_root,
                chapter_id,
                attempt,
                budget,
                exclude_run_id=run_id,
            )
            if stop_reason is not None:
                _atomic_write_yaml(
                    run_dir / "circuit_breaker.yaml",
                    {"status": "blocked", "reason": stop_reason, "chapter_id": chapter_id},
                )
                raise BudgetExceededError(stop_reason)
        _atomic_write_yaml(
            run_dir / "request.yaml",
            {
                "run_id": run_id,
                "chapter_id": chapter_id,
                "attempt": attempt,
                "binding_key": "chapter_draft",
                "context": context.model_dump(mode="json"),
            },
        )
        _atomic_write_yaml(run_dir / "prompt.yaml", {"messages": messages})

        if response_path.is_file():
            response = _load_response(response_path)
            _atomic_write_yaml(
                completion_path,
                {"status": "completed", "resumed_without_provider": True},
            )
            return ChapterDraftResult(run_id, run_dir, response, resumed=True)

        selected_gateway = gateway or LLMGateway(read.config)
        try:
            raw_response = selected_gateway.complete(
                "chapter_draft",
                messages,
                ChapterDraftResponse,
                prompt_template_name="book.chapter_draft.v1",
            )
            response = ChapterDraftResponse.model_validate(raw_response)
        except Exception as exc:
            _atomic_write_yaml(run_dir / "failure.yaml", {"error": str(exc)})
            raise

        _atomic_write_yaml(run_dir / "response.yaml", response.model_dump(mode="json"))
        calls = getattr(selected_gateway, "calls", [])
        _atomic_write_yaml(
            run_dir / "calls.yaml",
            {"calls": [call.model_dump(mode="json") for call in calls]},
        )
        _atomic_write_yaml(
            completion_path,
            {"status": "completed", "resumed_without_provider": False},
        )
        return ChapterDraftResult(run_id, run_dir, response, resumed=False)
