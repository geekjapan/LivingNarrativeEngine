"""Turn artifact loading for export-replay (export-replay/spec.md "turn artifactからの
replay.md組み立て"). Reads only what's needed to render — never touches state/gm_vault."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_LIVE_TURN_DIR_RE = re.compile(r"^turn_(\d+)$")


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class TurnRecord:
    turn: int
    status: str | None
    narration_body: str | None
    interventions: list[dict[str, Any]] = field(default_factory=list)
    rolls: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    diff: dict[str, Any] | None = None
    review_decision: str | None = None

    @property
    def is_body_turn(self) -> bool:
        """applied, and not a reject_all resolution (spec-foundation.md §9 D120)."""
        return self.status == "applied" and self.review_decision != "reject_all"

    @property
    def reader_visible_roll_ids(self) -> set[str]:
        """Roll ids reachable from a reader-visible event's ``roll_ids`` (D121): roll
        records carry no visibility of their own, so this is the only correct filter."""
        ids: set[str] = set()
        for event in self.events:
            if event.get("visibility") == "reader":
                ids.update(event.get("roll_ids") or [])
        return ids

    @property
    def reader_visible_rolls(self) -> list[dict[str, Any]]:
        allowed = self.reader_visible_roll_ids
        return [roll for roll in self.rolls if roll.get("id") in allowed]


def _read_narration_body(turn_dir: Path) -> str | None:
    path = turn_dir / "narration.md"
    if not path.exists():
        return None
    _, _, body = path.read_text(encoding="utf-8").partition("---\n\n")
    return body.rstrip("\n")


def _load_turn_record(turn_dir: Path, turn: int) -> TurnRecord:
    meta = _load_yaml(turn_dir / "meta.yaml") or {}
    intervention_file = _load_yaml(turn_dir / "intervention.yaml") or {}
    state_diff_file = _load_yaml(turn_dir / "state_diff.yaml")
    review_file = _load_yaml(turn_dir / "review.yaml")
    return TurnRecord(
        turn=turn,
        status=meta.get("status"),
        narration_body=_read_narration_body(turn_dir),
        interventions=intervention_file.get("interventions") or [],
        rolls=_load_yaml(turn_dir / "rolls.yaml") or [],
        events=_load_yaml(turn_dir / "events.yaml") or [],
        diff=state_diff_file,
        review_decision=(review_file or {}).get("decision") if review_file else None,
    )


def load_turn_records(runs_dir: Path) -> list[TurnRecord]:
    """Every *live* ``turn_NNNN`` (never ``_discarded_``), ascending by turn number."""
    if not runs_dir.exists():
        return []
    numbered = sorted(
        (int(match.group(1)), entry)
        for entry in runs_dir.iterdir()
        if entry.is_dir() and (match := _LIVE_TURN_DIR_RE.match(entry.name))
    )
    return [_load_turn_record(entry, turn) for turn, entry in numbered]
