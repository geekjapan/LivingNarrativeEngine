"""Weighted event table selection (design.md Risk mitigation: 1 selection = 1 float draw)."""

from collections.abc import Callable
from dataclasses import dataclass


class WeightedTableError(ValueError):
    pass


@dataclass(frozen=True)
class WeightedEntry:
    name: str
    weight: float


def select_weighted(
    entries: list[WeightedEntry],
    draw_float: Callable[[], float],
) -> WeightedEntry:
    if not entries:
        raise WeightedTableError("no eligible entries to select from")

    negative = [entry for entry in entries if entry.weight < 0]
    if negative:
        raise WeightedTableError(
            f"negative weight not allowed: {', '.join(e.name for e in negative)}"
        )

    total = sum(entry.weight for entry in entries)
    if total <= 0:
        raise WeightedTableError("total weight of eligible entries must be greater than 0")

    threshold = draw_float() * total
    cumulative = 0.0
    for entry in entries:
        cumulative += entry.weight
        if threshold < cumulative:
            return entry
    return entries[-1]  # floating point rounding guard
