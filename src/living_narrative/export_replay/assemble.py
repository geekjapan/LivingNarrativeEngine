"""Public export-replay entry point (export-replay/spec.md)."""

from pathlib import Path

from living_narrative.export_replay.loader import load_turn_records
from living_narrative.export_replay.render import RENDERERS


class UnknownReplayStyleError(ValueError):
    pass


class NoReplayableTurnsError(Exception):
    """No ``applied`` (non-``reject_all``) turn exists to build a replay from."""


def assemble_replay(runs_dir: Path, style: str) -> str:
    if style not in RENDERERS:
        raise UnknownReplayStyleError(f"unknown style: {style!r} (expected 'novel' or 'log')")

    records = load_turn_records(runs_dir)
    if not any(record.is_body_turn for record in records):
        raise NoReplayableTurnsError(
            "no applied (non-reject_all) turn exists yet — run `turn`/`auto` first"
        )

    return RENDERERS[style](records)
