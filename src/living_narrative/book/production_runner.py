"""CLI-first, recoverable orchestration for one long-form chapter production run."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from living_narrative.book.budget import BookBudgetPolicy, BudgetExceededError
from living_narrative.book.chapters import build_chapter_context, compile_chapter
from living_narrative.book.coordinator import (
    open_chapter_review,
    plan_generation,
    record_chapter_candidate,
    start_chapter_production,
)
from living_narrative.book.drafting import run_chapter_draft
from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.book.review import evaluate_semantic_continuity, review_chapter
from living_narrative.state.diff import fsync_directory
from living_narrative.state.models import ChapterLifecycle
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import WorkspacePaths, load_project


class ProductionRunPhase(StrEnum):
    """Observable progress for one durable chapter production run."""

    CREATED = "created"
    DRAFTING = "drafting"
    CANDIDATE_RECORDED = "candidate_recorded"
    AWAITING_AUTHOR = "awaiting_author"
    STOPPED = "stopped"
    FAILED = "failed"


class ChapterProductionRunStatus(BaseModel):
    """Reader-safe status projection for a chapter production run."""

    run_id: str
    chapter_id: str
    phase: ProductionRunPhase
    lifecycle: ChapterLifecycle
    draft_run_id: str | None = None
    attempt_id: str | None = None
    stopped_reason: str | None = None
    failure_code: str | None = None
    resumed: bool = False


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


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping artifact: {path.name}")
    return payload


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ChapterProductionRunner:
    """Run a chapter through draft, review evidence, and explicit author review.

    The runner deliberately delegates state mutation to ``coordinator`` and provider recovery to
    ``drafting``. Its own durable artifact only records public execution progress and links to
    those existing sources of truth.
    """

    def run(
        self,
        project_yaml: Path,
        chapter_id: str,
        *,
        gateway: Any | None = None,
        budget: BookBudgetPolicy | None = None,
    ) -> ChapterProductionRunStatus:
        read = load_project(project_yaml)
        if not read.is_valid or read.config is None or read.paths is None:
            raise ValueError(f"invalid project: {project_yaml}")

        paths = read.paths
        bundle = StateStore.load(paths.state)
        chapter = bundle.book_ledger.chapter(chapter_id)
        run_dir, run_id, revision = self._run_location(paths, bundle, chapter_id)
        resumed = (run_dir / "manifest.yaml").is_file()

        if chapter.lifecycle in {ChapterLifecycle.ACCEPTED, ChapterLifecycle.SUPERSEDED}:
            raise ValueError(
                f"chapter {chapter_id} cannot enter production from {chapter.lifecycle.value}"
            )

        try:
            if (run_dir / "manifest.yaml").is_file():
                self._assert_manifest_lifecycle(
                    _read_yaml(run_dir / "manifest.yaml"), chapter.lifecycle
                )
            if chapter.lifecycle is ChapterLifecycle.REVIEW:
                self._ensure_awaiting_author(run_dir, run_id, chapter_id)
                return self._status_from_disk(paths, chapter_id, run_dir, resumed=resumed)
            self._prepare_run(
                run_dir,
                run_id,
                chapter_id,
                plan_generation(bundle),
                revision,
            )
            if chapter.lifecycle is ChapterLifecycle.PLANNED:
                start_chapter_production(paths, chapter_id)
            if self._stop_if_requested(paths, chapter_id, run_dir, run_id, resumed=resumed):
                return self._status_from_disk(paths, chapter_id, run_dir, resumed=resumed)
            if chapter.lifecycle is ChapterLifecycle.CANDIDATE:
                open_chapter_review(paths, chapter_id)
                self._record_phase(
                    run_dir,
                    run_id,
                    chapter_id,
                    ProductionRunPhase.AWAITING_AUTHOR,
                    "awaiting_author",
                    {},
                )
                return self._status_from_disk(paths, chapter_id, run_dir, resumed=True)

            draft = run_chapter_draft(
                project_yaml,
                chapter_id,
                attempt=revision,
                gateway=gateway,
                budget=budget,
            )
            self._record_phase(
                run_dir,
                run_id,
                chapter_id,
                ProductionRunPhase.DRAFTING,
                "draft_completed",
                {
                    "draft_run_id": draft.run_id,
                    "resumed_without_provider": draft.resumed,
                },
            )

            if self._stop_if_requested(paths, chapter_id, run_dir, run_id, resumed=resumed):
                return self._status_from_disk(paths, chapter_id, run_dir, resumed=resumed)

            bundle = StateStore.load(paths.state)
            context = build_chapter_context(bundle, chapter_id, source_turns=[])
            candidate = compile_chapter(context, [draft.response.body])
            semantic = evaluate_semantic_continuity(context, candidate, gateway=gateway)
            review = review_chapter(context, candidate, semantic=semantic)
            record_chapter_candidate(paths, candidate, review, draft_run_id=draft.run_id)
            attempt_id = self._attempt_id(paths, chapter_id, draft.run_id)
            candidate_sha256 = hashlib.sha256(candidate.markdown.encode("utf-8")).hexdigest()
            _atomic_write_yaml(
                run_dir / "links.yaml",
                {
                    "draft_run_id": draft.run_id,
                    "candidate_sha256": candidate_sha256,
                    "attempt_id": attempt_id,
                },
            )
            self._record_phase(
                run_dir,
                run_id,
                chapter_id,
                ProductionRunPhase.CANDIDATE_RECORDED,
                "candidate_recorded",
                {"draft_run_id": draft.run_id, "attempt_id": attempt_id},
            )
            if self._stop_if_requested(paths, chapter_id, run_dir, run_id, resumed=resumed):
                return self._status_from_disk(paths, chapter_id, run_dir, resumed=resumed)

            open_chapter_review(paths, chapter_id)
            self._record_phase(
                run_dir,
                run_id,
                chapter_id,
                ProductionRunPhase.AWAITING_AUTHOR,
                "awaiting_author",
                {"attempt_id": attempt_id},
            )
        except BudgetExceededError as exc:
            _atomic_write_yaml(
                run_dir / "stop_requested.yaml",
                {
                    "requested_at": _utc_now(),
                    "reason": str(exc),
                    "source": "budget",
                    "consumed_at": _utc_now(),
                },
            )
            self._record_phase(
                run_dir,
                run_id,
                chapter_id,
                ProductionRunPhase.STOPPED,
                "stopped",
                {"stopped_reason": str(exc)},
            )
            return self._status_from_disk(paths, chapter_id, run_dir, resumed=resumed)
        except Exception as exc:
            self._record_failure(run_dir, run_id, chapter_id, exc)
            raise

        return self._status_from_disk(paths, chapter_id, run_dir, resumed=resumed)

    def status(self, project_yaml: Path, chapter_id: str) -> ChapterProductionRunStatus:
        read = load_project(project_yaml)
        if not read.is_valid or read.paths is None:
            raise ValueError(f"invalid project: {project_yaml}")
        bundle = StateStore.load(read.paths.state)
        run_dir, _, _ = self._run_location(read.paths, bundle, chapter_id)
        if not (run_dir / "manifest.yaml").is_file():
            raise ValueError(f"chapter production run not found: {chapter_id}")
        return self._status_from_disk(read.paths, chapter_id, run_dir, resumed=True)

    def request_stop(self, project_yaml: Path, chapter_id: str) -> ChapterProductionRunStatus:
        read = load_project(project_yaml)
        if not read.is_valid or read.paths is None:
            raise ValueError(f"invalid project: {project_yaml}")
        bundle = StateStore.load(read.paths.state)
        run_dir, run_id, _ = self._run_location(read.paths, bundle, chapter_id)
        if not (run_dir / "manifest.yaml").is_file():
            raise ValueError(f"chapter production run not found: {chapter_id}")
        _atomic_write_yaml(
            run_dir / "stop_requested.yaml",
            {"requested_at": _utc_now(), "reason": "author_requested"},
        )
        return self._status_from_disk(read.paths, chapter_id, run_dir, resumed=True)

    def _run_location(
        self,
        paths: WorkspacePaths,
        bundle: Any,
        chapter_id: str,
    ) -> tuple[Path, str, int]:
        generation = plan_generation(bundle)
        run_root = paths.runs / "chapter_production" / chapter_id
        lifecycle = bundle.book_ledger.chapter(chapter_id).lifecycle
        if (
            lifecycle
            in {
                ChapterLifecycle.RUNNING,
                ChapterLifecycle.CANDIDATE,
                ChapterLifecycle.REVIEW,
            }
            and run_root.is_dir()
        ):
            active_runs = sorted(
                (
                    item
                    for item in run_root.glob(f"generation_{generation}_revision_*")
                    if (item / "manifest.yaml").is_file()
                ),
                key=lambda item: item.name,
            )
            if active_runs:
                run_dir = active_runs[-1]
                run_id = run_dir.name
                revision = int(run_id.rsplit("_", 1)[-1])
                return run_dir, run_id, revision

        attempts = load_chapter_lineage(paths.root / "books" / "chapters", chapter_id).attempts
        revision = len(attempts) + 1
        run_id = f"generation_{generation}_revision_{revision:03d}"
        run_dir = run_root / run_id
        return run_dir, run_id, revision

    def _assert_manifest_lifecycle(
        self, manifest: dict[str, Any], lifecycle: ChapterLifecycle
    ) -> None:
        try:
            phase = ProductionRunPhase(str(manifest["phase"]))
        except (KeyError, ValueError) as exc:
            raise ValueError("inconsistent production run: invalid manifest phase") from exc
        allowed_lifecycles = {
            ProductionRunPhase.CREATED: {ChapterLifecycle.PLANNED, ChapterLifecycle.RUNNING},
            ProductionRunPhase.DRAFTING: {
                ChapterLifecycle.PLANNED,
                ChapterLifecycle.RUNNING,
                ChapterLifecycle.CANDIDATE,
                ChapterLifecycle.REVISING,
            },
            ProductionRunPhase.CANDIDATE_RECORDED: {ChapterLifecycle.CANDIDATE},
            ProductionRunPhase.AWAITING_AUTHOR: {ChapterLifecycle.REVIEW},
            ProductionRunPhase.STOPPED: {
                ChapterLifecycle.PLANNED,
                ChapterLifecycle.RUNNING,
                ChapterLifecycle.CANDIDATE,
                ChapterLifecycle.REVISING,
            },
            ProductionRunPhase.FAILED: set(ChapterLifecycle),
        }
        if lifecycle not in allowed_lifecycles[phase]:
            raise ValueError(
                "inconsistent production run: "
                f"phase {phase.value} cannot accompany lifecycle {lifecycle.value}"
            )

    def _prepare_run(
        self,
        run_dir: Path,
        run_id: str,
        chapter_id: str,
        generation: str,
        revision: int,
    ) -> None:
        manifest_path = run_dir / "manifest.yaml"
        if manifest_path.is_file():
            return
        _atomic_write_yaml(
            run_dir / "request.yaml",
            {
                "schema_version": 1,
                "run_id": run_id,
                "chapter_id": chapter_id,
                "requested_at": _utc_now(),
            },
        )
        self._record_phase(
            run_dir,
            run_id,
            chapter_id,
            ProductionRunPhase.DRAFTING,
            "preparing",
            {"generation": generation, "revision": revision},
        )

    def _record_phase(
        self,
        run_dir: Path,
        run_id: str,
        chapter_id: str,
        phase: ProductionRunPhase,
        event_name: str,
        details: dict[str, Any],
    ) -> None:
        events_dir = run_dir / "events"
        existing = sorted(events_dir.glob("*.yaml")) if events_dir.exists() else []
        event_path = events_dir / f"{len(existing) + 1:03d}_{event_name}.yaml"
        _atomic_write_yaml(
            event_path,
            {
                "schema_version": 1,
                "event": event_name,
                "phase": phase.value,
                "recorded_at": _utc_now(),
                **details,
            },
        )
        _atomic_write_yaml(
            run_dir / "manifest.yaml",
            {
                "schema_version": 1,
                "run_id": run_id,
                "chapter_id": chapter_id,
                "phase": phase.value,
                "updated_at": _utc_now(),
            },
        )

    def _ensure_awaiting_author(self, run_dir: Path, run_id: str, chapter_id: str) -> None:
        if not (run_dir / "manifest.yaml").is_file():
            self._prepare_run(run_dir, run_id, chapter_id, generation="unknown", revision=1)
        manifest = _read_yaml(run_dir / "manifest.yaml")
        if manifest.get("phase") != ProductionRunPhase.AWAITING_AUTHOR.value:
            self._record_phase(
                run_dir,
                run_id,
                chapter_id,
                ProductionRunPhase.AWAITING_AUTHOR,
                "awaiting_author",
                {},
            )

    def _stop_if_requested(
        self,
        paths: WorkspacePaths,
        chapter_id: str,
        run_dir: Path,
        run_id: str,
        *,
        resumed: bool,
    ) -> bool:
        stop_path = run_dir / "stop_requested.yaml"
        if not stop_path.is_file():
            return False
        stop = _read_yaml(stop_path)
        if stop.get("consumed_at") is not None:
            return False
        _atomic_write_yaml(stop_path, {**stop, "consumed_at": _utc_now()})
        self._record_phase(
            run_dir,
            run_id,
            chapter_id,
            ProductionRunPhase.STOPPED,
            "stopped",
            {"stopped_reason": str(stop.get("reason", "author_requested"))},
        )
        return True

    def _attempt_id(self, paths: WorkspacePaths, chapter_id: str, draft_run_id: str) -> str | None:
        lineage = load_chapter_lineage(paths.root / "books" / "chapters", chapter_id)
        match = next(
            (
                attempt
                for attempt in reversed(lineage.attempts)
                if attempt.draft_run_id == draft_run_id
            ),
            None,
        )
        return match.id if match is not None else None

    def _record_failure(self, run_dir: Path, run_id: str, chapter_id: str, exc: Exception) -> None:
        code = type(exc).__name__.lower()
        _atomic_write_yaml(run_dir / "failure.yaml", {"code": code, "recorded_at": _utc_now()})
        self._record_phase(
            run_dir,
            run_id,
            chapter_id,
            ProductionRunPhase.FAILED,
            "failed",
            {"failure_code": code},
        )

    def _status_from_disk(
        self,
        paths: WorkspacePaths,
        chapter_id: str,
        run_dir: Path,
        *,
        resumed: bool,
    ) -> ChapterProductionRunStatus:
        manifest = _read_yaml(run_dir / "manifest.yaml")
        links_path = run_dir / "links.yaml"
        failure_path = run_dir / "failure.yaml"
        stop_path = run_dir / "stop_requested.yaml"
        links = _read_yaml(links_path) if links_path.is_file() else {}
        failure = _read_yaml(failure_path) if failure_path.is_file() else {}
        stop = _read_yaml(stop_path) if stop_path.is_file() else {}
        lifecycle = StateStore.load(paths.state).book_ledger.chapter(chapter_id).lifecycle
        return ChapterProductionRunStatus(
            run_id=str(manifest["run_id"]),
            chapter_id=chapter_id,
            phase=ProductionRunPhase(str(manifest["phase"])),
            lifecycle=lifecycle,
            draft_run_id=links.get("draft_run_id"),
            attempt_id=links.get("attempt_id"),
            stopped_reason=stop.get("reason"),
            failure_code=(
                failure.get("code")
                if manifest.get("phase") == ProductionRunPhase.FAILED.value
                else None
            ),
            resumed=resumed,
        )
