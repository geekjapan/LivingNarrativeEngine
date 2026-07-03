from living_narrative.random.engine import RandomEngine
from living_narrative.random.tables import WeightedEntry


def _run_sequence(seed: str):
    engine = RandomEngine(seed)
    results = []
    results.append(engine.roll_dice("2d6+1", turn=1, target=8, label="attack"))
    results.append(engine.roll_chance(60, {"skill": 15, "injury": -20}, turn=1))
    entries = [
        WeightedEntry(name="ambush", weight=20),
        WeightedEntry(name="quiet_night", weight=80),
    ]
    results.append(engine.select_from_table(entries, turn=2, table_name="night_events"))
    results.append(engine.roll_dice("1d20", turn=2))
    return results, engine.draws_consumed


def test_identical_call_sequence_reproduces_all_roll_results():
    results_a, draws_a = _run_sequence("regression-seed-mist-station")
    results_b, draws_b = _run_sequence("regression-seed-mist-station")

    assert draws_a == draws_b
    for roll_a, roll_b in zip(results_a, results_b, strict=True):
        assert roll_a.result == roll_b.result
        assert roll_a.outcome == roll_b.outcome
        assert roll_a.type == roll_b.type


def test_different_seed_diverges_the_sequence():
    results_a, _ = _run_sequence("regression-seed-mist-station")
    results_b, _ = _run_sequence("regression-seed-other-station")

    assert [r.result for r in results_a] != [r.result for r in results_b]
