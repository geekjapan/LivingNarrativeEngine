"""Project-wide sequential ``int_NNNN`` id allocation (spec-foundation.md §3).

Mirrors ``pipeline/ids.py``'s event id allocator: it scans every turn's ``intervention.yaml``
(written every turn, even when empty) rather than the project-wide ``interventions.yaml``,
since the latter's write is deliberately delayed until a turn resolves (spec.md Requirement
"Intervention履歴インデックス").
"""

import re
from collections.abc import Callable
from pathlib import Path

import yaml

_INTERVENTION_ID_RE = re.compile(r"^int_(\d+)$")


def _max_intervention_number(runs_dir: Path) -> int:
    max_number = 0
    if not runs_dir.exists():
        return 0
    for entry in runs_dir.iterdir():
        intervention_path = entry / "intervention.yaml"
        if not entry.is_dir() or not intervention_path.exists():
            continue
        data = yaml.safe_load(intervention_path.read_text(encoding="utf-8")) or {}
        for item in data.get("interventions", []):
            match = _INTERVENTION_ID_RE.match(str(item.get("id", "")))
            if match:
                max_number = max(max_number, int(match.group(1)))
    return max_number


def make_intervention_id_allocator(runs_dir: Path) -> Callable[[], str]:
    """Return a callable that hands out fresh, project-wide-unique ``int_NNNN`` ids."""
    counter = _max_intervention_number(runs_dir)

    def allocate() -> str:
        nonlocal counter
        counter += 1
        return f"int_{counter:04d}"

    return allocate
