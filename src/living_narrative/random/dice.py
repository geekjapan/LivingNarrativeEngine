"""Dice notation parsing: ``NdM``, ``NdM+K``, ``NdM-K`` (spec-foundation.md §7)."""

import re
from dataclasses import dataclass

_DICE_PATTERN = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")

MAX_DICE_COUNT = 100
MAX_DICE_SIDES = 1000


class DiceParseError(ValueError):
    pass


@dataclass(frozen=True)
class DiceSpec:
    count: int
    sides: int
    modifier: int = 0


def parse_dice(notation: str) -> DiceSpec:
    match = _DICE_PATTERN.fullmatch(notation.strip())
    if not match:
        raise DiceParseError(f"invalid dice notation: {notation!r} (expected NdM, NdM+K, or NdM-K)")

    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if not 1 <= count <= MAX_DICE_COUNT:
        raise DiceParseError(f"dice count out of range 1-{MAX_DICE_COUNT}: {count}")
    if not 1 <= sides <= MAX_DICE_SIDES:
        raise DiceParseError(f"dice sides out of range 1-{MAX_DICE_SIDES}: {sides}")

    return DiceSpec(count=count, sides=sides, modifier=modifier)
