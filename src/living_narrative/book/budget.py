"""Deterministic preflight budget policy for recoverable chapter draft runs."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class BudgetExceededError(RuntimeError):
    """A draft run was stopped before a provider call by its explicit policy."""


class BookBudgetPolicy(BaseModel):
    """Bound attempt-based spend before provider-specific usage is available."""

    max_attempts_per_chapter: int | None = Field(default=None, ge=1)
    max_attempts_per_book: int | None = Field(default=None, ge=1)
    max_consecutive_revisions: int | None = Field(default=None, ge=1)


def _completed_or_started_attempt_count(runs_root: Path) -> int:
    if not runs_root.is_dir():
        return 0
    return sum(
        1
        for run_dir in runs_root.iterdir()
        if run_dir.is_dir() and run_dir.name.startswith("chapter_")
    )


def evaluate_draft_budget(
    runs_root: Path,
    chapter_id: str,
    attempt: int,
    policy: BookBudgetPolicy,
) -> str | None:
    """Return a stable stop reason, or ``None`` when a provider call is permitted."""
    if policy.max_attempts_per_chapter is not None and attempt > policy.max_attempts_per_chapter:
        return "chapter attempt budget exceeded"
    if policy.max_attempts_per_book is not None:
        existing = _completed_or_started_attempt_count(runs_root)
        if existing >= policy.max_attempts_per_book:
            return "book attempt budget exceeded"
    if (
        policy.max_consecutive_revisions is not None
        and attempt - 1 > policy.max_consecutive_revisions
    ):
        return "consecutive revision budget exceeded"
    return None
