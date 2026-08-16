"""Structured long-form planning without bypassing canonical state boundaries."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field, field_validator, model_validator

from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import (
    BookActPlan,
    BookChapterLedger,
    BookChapterPlan,
    BookLedgerState,
    BookPlanState,
    ChapterLifecycle,
    CharacterArcTarget,
    Visibility,
)


class StoryBibleWordRange(BaseModel):
    min_words: int = Field(ge=1)
    max_words: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_range(self) -> StoryBibleWordRange:
        if self.min_words > self.max_words:
            raise ValueError("min_words must not exceed max_words")
        return self


class StoryBibleCharacterArcTarget(BaseModel):
    character_id: str = Field(pattern=r"^char_\d+$")
    delta: str = Field(min_length=1)

    @field_validator("delta")
    @classmethod
    def _reject_blank_delta(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("character arc delta must not be blank")
        return value


class StoryBibleChapter(BaseModel):
    id: str = Field(pattern=r"^chapter_\d+$")
    act_id: str = Field(pattern=r"^act_\d+$")
    planned_goal: str = Field(min_length=1)
    required_thread_ids: list[str] = Field(default_factory=list)
    character_arc_targets: list[StoryBibleCharacterArcTarget] = Field(default_factory=list)
    target_word_range: StoryBibleWordRange

    @field_validator("planned_goal")
    @classmethod
    def _reject_blank_goal(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("planned_goal must not be blank")
        return value


class StoryBibleAct(BaseModel):
    id: str = Field(pattern=r"^act_\d+$")
    promise: str = Field(min_length=1)
    chapter_ids: list[str] = Field(default_factory=list)

    @field_validator("promise")
    @classmethod
    def _reject_blank_promise(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("act promise must not be blank")
        return value


class StoryBible(BaseModel):
    """Validated author input before it becomes a state-diff proposal."""

    premise: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    language: str = "ja"
    acts: list[StoryBibleAct] = Field(min_length=1)
    chapters: list[StoryBibleChapter] = Field(min_length=1)

    @field_validator("premise")
    @classmethod
    def _reject_blank_premise(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("premise must not be blank")
        return value

    @field_validator("audience")
    @classmethod
    def _reject_blank_audience(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("audience must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_structure(self) -> StoryBible:
        # Reuse the canonical BookPlan validation rather than maintaining a second
        # divergence-prone implementation of act/chapter membership rules.
        BookPlanState.model_validate(
            {
                "premise": self.premise,
                "audience": self.audience,
                "language": self.language,
                "acts": [act.model_dump(mode="json") for act in self.acts],
                "chapters": [chapter.model_dump(mode="json") for chapter in self.chapters],
            }
        )
        return self


class BookPlanProposal(BaseModel):
    """Reviewable proposal; it cannot mutate state until turned into a StateDiff."""

    proposal_id: str = Field(pattern=r"^book_plan_[a-f0-9]{64}$")
    book_plan: BookPlanState
    book_ledger: BookLedgerState


def build_book_plan_proposal(story_bible: StoryBible) -> BookPlanProposal:
    """Build a deterministic, structured plan proposal from validated author input."""
    plan = BookPlanState(
        premise=story_bible.premise,
        audience=story_bible.audience,
        language=story_bible.language,
        acts=[
            BookActPlan(
                id=act.id,
                promise=act.promise,
                chapter_ids=act.chapter_ids,
            )
            for act in story_bible.acts
        ],
        chapters=[
            BookChapterPlan(
                id=chapter.id,
                act_id=chapter.act_id,
                planned_goal=chapter.planned_goal,
                required_thread_ids=chapter.required_thread_ids,
                character_arc_targets=[
                    CharacterArcTarget(
                        character_id=target.character_id,
                        delta=target.delta,
                    )
                    for target in chapter.character_arc_targets
                ],
                target_word_range={
                    "min_words": chapter.target_word_range.min_words,
                    "max_words": chapter.target_word_range.max_words,
                },
            )
            for chapter in story_bible.chapters
        ],
    )
    ledger = BookLedgerState(
        active_chapter_id=plan.chapters[0].id,
        chapters=[
            BookChapterLedger(id=chapter.id, lifecycle=ChapterLifecycle.PLANNED)
            for chapter in plan.chapters
        ],
        next_action="start_chapter",
    )
    canonical = json.dumps(
        {"book_plan": plan.model_dump(mode="json"), "book_ledger": ledger.model_dump(mode="json")},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return BookPlanProposal(
        proposal_id=f"book_plan_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}",
        book_plan=plan,
        book_ledger=ledger,
    )


def proposal_to_state_diff(proposal: BookPlanProposal, *, turn: int) -> StateDiff:
    """Return the explicit, reviewable state change for an accepted proposal."""
    return StateDiff(
        id=f"diff_{turn:04d}",
        turn=turn,
        changes=[
            StateDiffChange(
                target="book_plan",
                op="set",
                value=proposal.book_plan.model_dump(mode="json"),
                visibility=Visibility.CANON,
            ),
            StateDiffChange(
                target="book_ledger",
                op="set",
                value=proposal.book_ledger.model_dump(mode="json"),
                visibility=Visibility.GM_ONLY,
            ),
        ],
    )
