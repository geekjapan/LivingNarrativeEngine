"""Narrator input/output models (spec-foundation.md §4.3 invariant 2)."""

from pydantic import BaseModel, Field

from living_narrative.state.models import Event


class NarratorContext(BaseModel):
    """Everything the Narrator may see: reader-visible only, never GM Vault/hidden_facts/secrets."""

    turn: int
    reader_state_facts: list[str] = Field(default_factory=list)
    scene_reader_visible_facts: list[str] = Field(default_factory=list)
    reader_visible_events: list[Event] = Field(default_factory=list)


class NarrationResult(BaseModel):
    text: str
    style: str
