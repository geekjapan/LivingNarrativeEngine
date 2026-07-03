"""Cross-turn RNG continuity: cumulative draws consumed, project-wide roll history (D112)."""

from pathlib import Path

import yaml

from living_narrative.pipeline.turn_numbering import ANY_TURN_DIR_RE
from living_narrative.random.models import Roll


def total_rng_draws_consumed(runs_dir: Path) -> int:
    """Sum ``rng_draws_consumed`` across every ``turn_*`` and ``turn_*_discarded_*`` meta.yaml.

    Each attempt records only its own draws (never a retry's discarded predecessor's total),
    so the project-wide cumulative figure is this unweighted sum with no double counting.
    """
    total = 0
    if not runs_dir.exists():
        return 0
    for entry in runs_dir.iterdir():
        if not entry.is_dir() or not ANY_TURN_DIR_RE.match(entry.name):
            continue
        meta_path = entry / "meta.yaml"
        if not meta_path.exists():
            continue
        try:
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        total += int(data.get("rng_draws_consumed") or 0)
    return total


def load_all_rolls(runs_dir: Path) -> list[Roll]:
    """Concatenate ``rolls.yaml`` across every turn dir, for project-wide roll id uniqueness."""
    rolls: list[Roll] = []
    if not runs_dir.exists():
        return rolls
    for entry in runs_dir.iterdir():
        if not entry.is_dir() or not ANY_TURN_DIR_RE.match(entry.name):
            continue
        rolls_path = entry / "rolls.yaml"
        if not rolls_path.exists():
            continue
        raw = yaml.safe_load(rolls_path.read_text(encoding="utf-8")) or []
        rolls.extend(Roll.model_validate(item) for item in raw)
    return rolls
