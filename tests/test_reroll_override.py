from living_narrative.random.engine import RandomEngine


def test_reroll_creates_new_record_referencing_original():
    engine = RandomEngine("seed-reroll-a")
    original = engine.roll_dice("2d6", turn=1, target=7)
    rerolled = engine.reroll(original, turn=1)

    assert rerolled.id != original.id
    assert rerolled.supersedes == original.id
    assert rerolled.type == "dice"
    assert rerolled.dice.notation == "2d6"
    assert rerolled.dice.target == 7


def test_reroll_does_not_mutate_original_record():
    engine = RandomEngine("seed-reroll-b")
    original = engine.roll_dice("1d6", turn=1)
    original_snapshot = original.model_copy(deep=True)

    engine.reroll(original, turn=1)

    assert original == original_snapshot


def test_reroll_draws_from_current_stream_position_not_replayed():
    engine = RandomEngine("seed-reroll-c")
    original = engine.roll_dice("3d6", turn=1)
    draws_before_reroll = engine.draws_consumed

    rerolled = engine.reroll(original, turn=1)

    assert engine.draws_consumed == draws_before_reroll + 3
    # Rerolling from the current stream position, not rewinding, means the
    # reroll result need not equal the original (same seed, later position).
    assert isinstance(rerolled.result, int)


def test_reroll_same_type_and_consumption_for_chance():
    engine = RandomEngine("seed-reroll-d")
    original = engine.roll_chance(50, {"bonus": 10}, turn=1)
    draws_before = engine.draws_consumed

    rerolled = engine.reroll(original, turn=1)

    assert rerolled.chance.base_chance == 50
    assert rerolled.chance.modifiers == {"bonus": 10}
    assert engine.draws_consumed == draws_before + 1


def test_override_creates_new_record_and_consumes_no_draws():
    engine = RandomEngine("seed-override-a")
    original = engine.roll_dice("2d6", turn=1, target=7)
    draws_before = engine.draws_consumed

    overridden = engine.override_roll(original, turn=1, result=12, outcome="success")

    assert overridden.id != original.id
    assert overridden.supersedes == original.id
    assert overridden.override is True
    assert overridden.result == 12
    assert overridden.outcome == "success"
    assert engine.draws_consumed == draws_before


def test_override_does_not_mutate_original_record():
    engine = RandomEngine("seed-override-b")
    original = engine.roll_dice("2d6", turn=1, target=7)
    original_snapshot = original.model_copy(deep=True)

    engine.override_roll(original, turn=1, result=12, outcome="success")

    assert original == original_snapshot
    assert original.override is False
