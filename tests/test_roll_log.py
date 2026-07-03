import yaml

from living_narrative.random.engine import RandomEngine, append_roll, load_rolls


def test_append_roll_writes_new_file(tmp_path):
    rolls_path = tmp_path / "turn_0001" / "rolls.yaml"
    engine = RandomEngine("seed-log-a")
    roll = engine.roll_dice("2d6", turn=1)

    append_roll(rolls_path, roll)

    loaded = load_rolls(rolls_path)
    assert len(loaded) == 1
    assert loaded[0].id == roll.id
    assert loaded[0].dice.notation == "2d6"


def test_append_roll_preserves_existing_records(tmp_path):
    rolls_path = tmp_path / "rolls.yaml"
    engine = RandomEngine("seed-log-b")

    first = engine.roll_dice("1d6", turn=1)
    append_roll(rolls_path, first)
    second = engine.roll_chance(50, turn=1)
    append_roll(rolls_path, second)

    loaded = load_rolls(rolls_path)
    assert [item.id for item in loaded] == [first.id, second.id]


def test_load_rolls_missing_file_returns_empty_list(tmp_path):
    assert load_rolls(tmp_path / "does_not_exist.yaml") == []


def test_roll_id_is_globally_unique_across_turns(tmp_path):
    rolls_path = tmp_path / "rolls.yaml"
    engine = RandomEngine("seed-log-c")
    for turn in range(1, 4):
        append_roll(rolls_path, engine.roll_dice("1d6", turn=turn))

    loaded = load_rolls(rolls_path)
    assert len({item.id for item in loaded}) == len(loaded) == 3


def test_label_and_consequences_pass_through_untouched(tmp_path):
    engine = RandomEngine("seed-log-d")
    roll = engine.roll_dice(
        "1d6",
        turn=1,
        label="stealth_check",
        consequences=["リナは追跡者に気づかない"],
    )
    assert roll.label == "stealth_check"
    assert roll.consequences == ["リナは追跡者に気づかない"]

    rolls_path = tmp_path / "rolls.yaml"
    append_roll(rolls_path, roll)
    raw = yaml.safe_load(rolls_path.read_text(encoding="utf-8"))
    assert raw[0]["label"] == "stealth_check"
    assert raw[0]["consequences"] == ["リナは追跡者に気づかない"]


def test_severity_passthrough_is_not_auto_judged(tmp_path):
    engine = RandomEngine("seed-log-e")
    roll = engine.roll_dice("1d6", turn=1, target=5, severity="critical")
    assert roll.severity == "critical"

    rolls_path = tmp_path / "rolls.yaml"
    append_roll(rolls_path, roll)
    loaded = load_rolls(rolls_path)
    assert loaded[0].severity == "critical"


def test_default_severity_is_normal():
    engine = RandomEngine("seed-log-f")
    roll = engine.roll_dice("1d6", turn=1)
    assert roll.severity == "normal"
