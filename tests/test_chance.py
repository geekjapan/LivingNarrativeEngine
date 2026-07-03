from living_narrative.random.engine import RandomEngine


def test_final_chance_combines_modifiers():
    engine = RandomEngine("seed-chance-a")
    roll = engine.roll_chance(55, {"weather": 10, "fatigue": -15}, turn=1)
    assert roll.chance.final_chance == 50
    assert roll.chance.base_chance == 55
    assert roll.chance.modifiers == {"weather": 10, "fatigue": -15}


def test_final_chance_clamps_above_100():
    engine = RandomEngine("seed-chance-b")
    roll = engine.roll_chance(90, {"boost": 50}, turn=1)
    assert roll.chance.final_chance == 100


def test_final_chance_clamps_below_0():
    engine = RandomEngine("seed-chance-c")
    roll = engine.roll_chance(10, {"penalty": -50}, turn=1)
    assert roll.chance.final_chance == 0


def test_outcome_matches_roll_value_vs_final_chance():
    engine = RandomEngine("seed-chance-d")
    for _ in range(50):
        roll = engine.roll_chance(50, turn=1)
        expected = "success" if roll.chance.roll_value <= roll.chance.final_chance else "failure"
        assert roll.outcome == expected
        assert 1 <= roll.chance.roll_value <= 100


def test_chance_roll_consumes_one_draw():
    engine = RandomEngine("seed-chance-e")
    engine.roll_chance(50, turn=1)
    assert engine.draws_consumed == 1


def test_same_seed_same_order_reproduces_result():
    engine_a = RandomEngine("seed-chance-repro")
    engine_b = RandomEngine("seed-chance-repro")
    roll_a = engine_a.roll_chance(50, turn=1)
    roll_b = engine_b.roll_chance(50, turn=1)
    assert roll_a.chance.roll_value == roll_b.chance.roll_value
    assert roll_a.outcome == roll_b.outcome
