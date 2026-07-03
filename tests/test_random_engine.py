from living_narrative.random.engine import RandomEngine, next_roll_number, seed_to_int


def test_seed_to_int_is_stable():
    assert seed_to_int("20260703-mist-city") == seed_to_int("20260703-mist-city")


def test_same_seed_produces_same_draw_sequence():
    engine_a = RandomEngine("same-seed")
    engine_b = RandomEngine("same-seed")
    draws_a = [engine_a._draw_float() for _ in range(20)]
    draws_b = [engine_b._draw_float() for _ in range(20)]
    assert draws_a == draws_b


def test_different_seeds_produce_different_sequences():
    engine_a = RandomEngine("seed-one")
    engine_b = RandomEngine("seed-two")
    draws_a = [engine_a._draw_float() for _ in range(20)]
    draws_b = [engine_b._draw_float() for _ in range(20)]
    assert draws_a != draws_b


def test_reconstruction_from_draw_count_continues_sequence():
    continuous = RandomEngine("resume-seed")
    before = [continuous._draw_float() for _ in range(5)]
    continued = [continuous._draw_float() for _ in range(3)]

    resumed = RandomEngine("resume-seed", draws_consumed=5)
    resumed_draws = [resumed._draw_float() for _ in range(3)]

    assert resumed_draws == continued
    assert resumed.draws_consumed == 8
    assert len(before) == 5


def test_gm_override_advances_roll_id_but_not_draws():
    engine = RandomEngine("seed-override-draws")
    original = engine.roll_dice("1d6", turn=1)
    draws_before_override = engine.draws_consumed

    overridden = engine.override_roll(original, turn=1, result=6, outcome="success")
    assert engine.draws_consumed == draws_before_override
    assert overridden.id != original.id

    next_roll = engine.roll_dice("1d6", turn=1)
    assert engine.draws_consumed == draws_before_override + 1
    assert next_roll.id != overridden.id


def test_next_roll_number_from_existing_rolls():
    engine = RandomEngine("seed-roll-number")
    rolls = [engine.roll_dice("1d6", turn=1) for _ in range(3)]
    assert next_roll_number(rolls) == 4


def test_next_roll_number_with_no_existing_rolls():
    assert next_roll_number([]) == 1


def test_turn_draw_delta_is_queryable():
    engine = RandomEngine("seed-turn-delta")
    baseline = engine.draws_consumed
    engine.roll_dice("2d6", turn=1)
    engine.roll_chance(50, turn=1)
    assert engine.draws_consumed - baseline == 3
