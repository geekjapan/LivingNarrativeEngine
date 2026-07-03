# Random Engine

The random-engine capability is the single deterministic RNG stream used by all dice rolls,
probability checks, and weighted table selections. It follows `docs/spec-foundation.md` §7
and `openspec/changes/add-random-engine/design.md` for the seed/draw-count contract.

## Seed

`RandomEngine(random_seed)` hashes the project's `random_seed` string (SHA-256 → integer) and
seeds a `random.Random` stream from it. Every draw — one dice face, one d100 chance roll, or
one table selection — consumes exactly one call to the underlying float generator, so the same
`random_seed` + same call order always reproduces the same roll results.

```python
from living_narrative.random.engine import RandomEngine

engine = RandomEngine(project.random_seed)
```

### Resume

RNG state is never serialized directly. To resume, re-create the engine from the seed and the
number of draws already consumed (e.g. from the last turn's `meta.yaml` `rng_draws_consumed`);
the engine fast-forwards by discarding that many draws before continuing:

```python
engine = RandomEngine(project.random_seed, draws_consumed=previous_draws)
```

`engine.draws_consumed` reports the running total; diff it against a turn-start snapshot to get
the draws used in a single turn.

## Dice notation

`NdM`, `NdM+K`, `NdM-K` with `1 <= N <= 100` and `1 <= M <= 1000`:

```python
roll = engine.roll_dice("2d6+3", turn=1, target=10)  # target is optional
roll.result   # int
roll.outcome  # "success" | "failure" | None (None when target is omitted)
```

## Probability checks

```python
roll = engine.roll_chance(55, {"weather": 10, "fatigue": -15}, turn=1)
roll.chance.final_chance  # base_chance + sum(modifiers), clamped to [0, 100]
roll.outcome              # "success" if d100 roll <= final_chance else "failure"
```

## Weighted tables

Condition evaluation is the caller's responsibility — pass only the eligible entries:

```python
from living_narrative.random.tables import WeightedEntry

roll = engine.select_from_table(
    [WeightedEntry(name="ambush", weight=20), WeightedEntry(name="quiet_night", weight=80)],
    turn=1,
    table_name="night_events",
)
roll.result  # the selected entry's name
```

## Roll log

Every roll returned by the engine is a `Roll` (see `living_narrative/random/models.py`) and can
be appended to a turn artifact's `rolls.yaml`:

```python
from living_narrative.random.engine import append_roll, load_rolls

append_roll(turn_dir / "rolls.yaml", roll)
rolls = load_rolls(turn_dir / "rolls.yaml")
```

`label` and `consequences` are opaque pass-through fields; `severity` (`normal`/`critical`) is
also a pass-through set by the caller (e.g. Conflict Resolver) — the engine never infers it.

## Reroll and GM override

Both create a new `Roll` that references the original via `supersedes`; neither mutates the
original record.

```python
rerolled = engine.reroll(original_roll, turn=1)       # same type/consumption, new draws
overridden = engine.override_roll(original_roll, turn=1, result=12, outcome="success")
```

`reroll` draws from the current stream position (never rewinds) and consumes the same number of
draws as the original roll type. `override_roll` consumes zero RNG draws.
