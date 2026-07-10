"""Narrator input/output models (spec-foundation.md §4.3 invariant 2)."""

from typing import Literal

from pydantic import BaseModel, Field

from living_narrative.state.models import Event, OpenQuestInfo


class ThreadUpdateCandidate(BaseModel):
    """Issue 014: a narrator-proposed change to the unresolved-thread ledger.

    ``open`` requires ``description`` (a new mystery/thread, sourced only from reader-visible
    material -> leak-safe by construction). ``advance``/``resolve`` require ``thread_id``;
    ``note`` is an optional progress summary for ``advance``. Unknown/invalid combinations are
    rejected downstream by the State Manager, not here.
    """

    action: Literal["open", "advance", "resolve"]
    thread_id: str | None = None
    description: str | None = None
    note: str | None = None


class NarratorQuestUpdateCandidate(BaseModel):
    """A reader-context narrator proposal, including opening a public quest."""

    action: Literal["open", "advance", "resolve"]
    quest_id: str
    title: str | None = None
    objectives: list[str] = Field(default_factory=list)


class OpenThreadInfo(BaseModel):
    """A single open (non-resolved) unresolved thread, as surfaced to the Narrator."""

    id: str
    description: str
    opened_turn: int | None = None


class NarratorContext(BaseModel):
    """Everything the Narrator may see: reader-visible only, never GM Vault/hidden_facts/secrets."""

    turn: int
    reader_state_facts: list[str] = Field(default_factory=list)
    scene_reader_visible_facts: list[str] = Field(default_factory=list)
    reader_visible_events: list[Event] = Field(default_factory=list)
    scene_summary: str = ""
    open_threads: list[OpenThreadInfo] = Field(default_factory=list)
    open_quests: list[OpenQuestInfo] = Field(default_factory=list)
    # Issue 015: latest memory-summary text (empty when none yet), always available for
    # consumption like scene_summary; memory_summary_due/summary_window_events are only
    # populated on turns where the narrator is asked to (re)write it.
    memory_summary: str = ""
    memory_summary_due: bool = False
    summary_window_events: list[str] = Field(default_factory=list)


class NarrationResult(BaseModel):
    text: str
    style: str
    scene_summary_update: str | None = None
    thread_updates: list[ThreadUpdateCandidate] = Field(default_factory=list)
    quest_updates: list[NarratorQuestUpdateCandidate] = Field(default_factory=list)
    memory_summary_update: str | None = None
