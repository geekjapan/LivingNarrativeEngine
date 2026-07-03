"""Rerun helpers: discard attempts and compute replay RNG offsets."""

from pathlib import Path

import yaml

from living_narrative.intervention.history import mark_superseded_by_rerun
from living_narrative.pipeline.turn_numbering import discard_turn_directory
from living_narrative.session.review import _load_events


def discard_for_rerun(turn_dir: Path, interventions_path: Path) -> Path:
    event_ids = {event.id for event in _load_events(turn_dir)}
    discarded = discard_turn_directory(turn_dir)
    mark_superseded_by_rerun(interventions_path, event_ids)
    return discarded


def rerun_rng_offset(runs_dir: Path, turn: int, *, replay_same_seed: bool) -> int:
    total = 0
    if not runs_dir.exists():
        return 0
    for entry in runs_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith("turn_"):
            continue
        try:
            entry_turn = int(entry.name.split("_")[1])
        except (IndexError, ValueError):
            continue
        if entry_turn < turn or (entry_turn == turn and not replay_same_seed):
            meta_path = entry / "meta.yaml"
            if meta_path.exists():
                data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
                total += int(data.get("rng_draws_consumed") or 0)
    return total
