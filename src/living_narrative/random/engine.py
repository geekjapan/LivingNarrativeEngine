"""Deterministic RNG core: seed hashing, roll id/draw counters, roll log persistence.

See design.md D1-D6 and D123 for the decisions this module implements.
"""

import hashlib
import os
import random
from pathlib import Path
from typing import Any

import yaml

from living_narrative.random.dice import parse_dice
from living_narrative.random.models import ChanceInput, DiceInput, Roll, TableEntryInput, TableInput
from living_narrative.random.tables import WeightedEntry, select_weighted


def seed_to_int(random_seed: str) -> int:
    """Stable, platform-independent seed hash (design.md D1)."""
    return int(hashlib.sha256(random_seed.encode("utf-8")).hexdigest(), 16)


def next_roll_number(existing_rolls: list[Roll]) -> int:
    """Next project-wide roll id number after the highest one in ``existing_rolls``."""
    if not existing_rolls:
        return 1
    return max(int(roll.id.split("_")[1]) for roll in existing_rolls) + 1


class RandomEngine:
    """Single project-level RNG stream (design.md D2).

    Every draw — dice face, d100 chance roll, or table selection — consumes exactly one
    call to the underlying float generator (design.md D5, Risk mitigation for tables),
    so RNG state can be reconstructed from ``random_seed`` + draw count alone (D3),
    independent of which logical operation performed the draw.
    """

    def __init__(self, random_seed: str, draws_consumed: int = 0, next_roll_number: int = 1):
        self._rng = random.Random(seed_to_int(random_seed))
        for _ in range(draws_consumed):
            self._rng.random()
        self._draws_consumed = draws_consumed
        self._next_roll_number = next_roll_number

    @property
    def draws_consumed(self) -> int:
        return self._draws_consumed

    def _draw_float(self) -> float:
        value = self._rng.random()
        self._draws_consumed += 1
        return value

    def _new_id(self) -> str:
        roll_id = f"roll_{self._next_roll_number:04d}"
        self._next_roll_number += 1
        return roll_id

    def roll_dice(
        self,
        notation: str,
        *,
        turn: int,
        target: int | None = None,
        label: str | None = None,
        consequences: list[str] | None = None,
        severity: str = "normal",
    ) -> Roll:
        spec = parse_dice(notation)
        faces = [int(self._draw_float() * spec.sides) + 1 for _ in range(spec.count)]
        result = sum(faces) + spec.modifier
        outcome = None if target is None else ("success" if result >= target else "failure")
        return Roll(
            id=self._new_id(),
            turn=turn,
            type="dice",
            dice=DiceInput(notation=notation, target=target, faces=faces),
            result=result,
            outcome=outcome,
            label=label,
            consequences=consequences or [],
            severity=severity,
        )

    def roll_chance(
        self,
        base_chance: int,
        modifiers: dict[str, int] | None = None,
        *,
        turn: int,
        label: str | None = None,
        consequences: list[str] | None = None,
        severity: str = "normal",
    ) -> Roll:
        modifiers = modifiers or {}
        final_chance = max(0, min(100, base_chance + sum(modifiers.values())))
        roll_value = int(self._draw_float() * 100) + 1
        outcome = "success" if roll_value <= final_chance else "failure"
        return Roll(
            id=self._new_id(),
            turn=turn,
            type="chance",
            chance=ChanceInput(
                base_chance=base_chance,
                modifiers=modifiers,
                final_chance=final_chance,
                roll_value=roll_value,
            ),
            result=roll_value,
            outcome=outcome,
            label=label,
            consequences=consequences or [],
            severity=severity,
        )

    def select_from_table(
        self,
        entries: list[WeightedEntry],
        *,
        turn: int,
        table_name: str | None = None,
        label: str | None = None,
        consequences: list[str] | None = None,
        severity: str = "normal",
    ) -> Roll:
        selected = select_weighted(entries, self._draw_float)
        return Roll(
            id=self._new_id(),
            turn=turn,
            type="table",
            table=TableInput(
                table=table_name,
                entries=[TableEntryInput(name=e.name, weight=e.weight) for e in entries],
            ),
            result=selected.name,
            label=label,
            consequences=consequences or [],
            severity=severity,
        )

    def reroll(
        self,
        original: Roll,
        *,
        turn: int,
        label: str | None = None,
        consequences: list[str] | None = None,
        severity: str | None = None,
    ) -> Roll:
        """Re-execute ``original`` as a new roll from the current stream position (D4)."""
        kwargs: dict[str, Any] = {
            "turn": turn,
            "label": label if label is not None else original.label,
            "consequences": consequences if consequences is not None else original.consequences,
            "severity": severity if severity is not None else original.severity,
        }
        if original.type == "dice":
            new_roll = self.roll_dice(original.dice.notation, target=original.dice.target, **kwargs)
        elif original.type == "chance":
            new_roll = self.roll_chance(
                original.chance.base_chance, original.chance.modifiers, **kwargs
            )
        elif original.type == "table":
            entries = [WeightedEntry(name=e.name, weight=e.weight) for e in original.table.entries]
            new_roll = self.select_from_table(entries, table_name=original.table.table, **kwargs)
        else:  # pragma: no cover - Roll.type is a closed Literal
            raise ValueError(f"unknown roll type: {original.type}")
        return new_roll.model_copy(update={"supersedes": original.id})

    def override_roll(
        self,
        original: Roll,
        *,
        turn: int,
        result: Any,
        outcome: str | None = None,
        label: str | None = None,
        consequences: list[str] | None = None,
    ) -> Roll:
        """Record a GM override. Consumes no RNG draws (D6/spec: GM override draws=0)."""
        return Roll(
            id=self._new_id(),
            turn=turn,
            type=original.type,
            dice=original.dice,
            chance=original.chance,
            table=original.table,
            result=result,
            outcome=outcome if outcome is not None else original.outcome,
            label=label if label is not None else original.label,
            consequences=consequences if consequences is not None else original.consequences,
            supersedes=original.id,
            override=True,
            severity=original.severity,
        )


def load_rolls(rolls_path: Path) -> list[Roll]:
    if not rolls_path.exists():
        return []
    raw = yaml.safe_load(rolls_path.read_text(encoding="utf-8")) or []
    return [Roll.model_validate(item) for item in raw]


def append_roll(rolls_path: Path, roll: Roll) -> None:
    rolls = load_rolls(rolls_path)
    rolls.append(roll)
    rolls_path.parent.mkdir(parents=True, exist_ok=True)
    data = [item.model_dump(mode="json") for item in rolls]
    tmp = rolls_path.with_suffix(f"{rolls_path.suffix}.tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, rolls_path)
