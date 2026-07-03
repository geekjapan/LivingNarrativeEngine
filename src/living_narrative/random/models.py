"""Roll record schema persisted to ``rolls.yaml`` (random-engine spec, spec-foundation.md D123)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from living_narrative.state.models import RollId

RollType = Literal["dice", "chance", "table"]
Outcome = Literal["success", "failure"]
Severity = Literal["normal", "critical"]


class DiceInput(BaseModel):
    notation: str
    target: int | None = None
    faces: list[int] = Field(default_factory=list)


class ChanceInput(BaseModel):
    base_chance: int
    modifiers: dict[str, int] = Field(default_factory=dict)
    final_chance: int
    roll_value: int


class TableEntryInput(BaseModel):
    name: str
    weight: float


class TableInput(BaseModel):
    table: str | None = None
    entries: list[TableEntryInput] = Field(default_factory=list)


class Roll(BaseModel):
    """A single roll record. Exactly one of ``dice``/``chance``/``table`` is set, per ``type``."""

    model_config = {"extra": "allow"}

    id: RollId
    turn: int
    type: RollType
    dice: DiceInput | None = None
    chance: ChanceInput | None = None
    table: TableInput | None = None
    result: Any = None
    outcome: Outcome | None = None
    label: str | None = None
    consequences: list[str] = Field(default_factory=list)
    supersedes: RollId | None = None
    override: bool = False
    severity: Severity = "normal"
