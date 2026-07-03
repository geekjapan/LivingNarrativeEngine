from collections import Counter

import pytest

from living_narrative.random.engine import RandomEngine
from living_narrative.random.tables import WeightedEntry, WeightedTableError, select_weighted


def test_selection_converges_to_weight_ratio():
    entries = [WeightedEntry(name="common", weight=70), WeightedEntry(name="rare", weight=30)]
    engine = RandomEngine("seed-table-a")
    counts = Counter(engine.select_from_table(entries, turn=1).result for _ in range(900))
    ratio = counts["common"] / (counts["common"] + counts["rare"])
    assert 0.63 <= ratio <= 0.77


def test_table_selection_consumes_one_draw():
    entries = [WeightedEntry(name="a", weight=1), WeightedEntry(name="b", weight=1)]
    engine = RandomEngine("seed-table-b")
    engine.select_from_table(entries, turn=1)
    assert engine.draws_consumed == 1


def test_empty_entries_raises():
    with pytest.raises(WeightedTableError):
        select_weighted([], lambda: 0.5)


def test_zero_total_weight_raises():
    entries = [WeightedEntry(name="a", weight=0), WeightedEntry(name="b", weight=0)]
    with pytest.raises(WeightedTableError):
        select_weighted(entries, lambda: 0.5)


def test_negative_weight_raises():
    entries = [WeightedEntry(name="a", weight=10), WeightedEntry(name="b", weight=-5)]
    with pytest.raises(WeightedTableError):
        select_weighted(entries, lambda: 0.5)


def test_table_roll_records_eligible_entries():
    entries = [WeightedEntry(name="a", weight=70), WeightedEntry(name="b", weight=30)]
    engine = RandomEngine("seed-table-c")
    roll = engine.select_from_table(entries, turn=1, table_name="encounter_table")
    assert roll.table.table == "encounter_table"
    assert {e.name: e.weight for e in roll.table.entries} == {"a": 70, "b": 30}
    assert roll.result in {"a", "b"}
