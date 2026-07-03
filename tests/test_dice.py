import pytest

from living_narrative.random.dice import DiceParseError, DiceSpec, parse_dice
from living_narrative.random.engine import RandomEngine


def test_parses_dice_with_positive_modifier():
    assert parse_dice("2d6+3") == DiceSpec(count=2, sides=6, modifier=3)


def test_parses_dice_with_negative_modifier():
    assert parse_dice("3d8-2") == DiceSpec(count=3, sides=8, modifier=-2)


def test_parses_dice_without_modifier():
    assert parse_dice("1d20") == DiceSpec(count=1, sides=20, modifier=0)


def test_rejects_dice_count_over_limit():
    with pytest.raises(DiceParseError):
        parse_dice("101d6")


def test_rejects_dice_sides_over_limit():
    with pytest.raises(DiceParseError):
        parse_dice("2d1001")


@pytest.mark.parametrize("notation", ["d6", "2x6", "2d", "2d6x3", ""])
def test_rejects_malformed_notation(notation):
    with pytest.raises(DiceParseError):
        parse_dice(notation)


def test_dice_roll_result_within_expected_range():
    engine = RandomEngine("seed-a")
    for _ in range(50):
        roll = engine.roll_dice("2d6+3", turn=1)
        assert 5 <= roll.result <= 15
        assert roll.dice.notation == "2d6+3"
        assert len(roll.dice.faces) == 2
        assert all(1 <= face <= 6 for face in roll.dice.faces)
        assert roll.outcome is None


def test_dice_roll_with_target_success():
    engine = RandomEngine("seed-b")
    roll = engine.roll_dice("2d6", turn=1, target=7)
    assert roll.dice.target == 7
    expected_outcome = "success" if roll.result >= 7 else "failure"
    assert roll.outcome == expected_outcome


def test_dice_roll_consumes_n_draws():
    engine = RandomEngine("seed-c")
    engine.roll_dice("3d6", turn=1)
    assert engine.draws_consumed == 3
