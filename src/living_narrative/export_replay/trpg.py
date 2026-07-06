"""GM-facing TRPG-style replay export (docs/issues/028-029): extends the reader-safe ``log``
style (``render.py``) with full roll visibility, GM-flavored intervention lines, and scene
headings recovered from Issue 026's scene reconstruction.

This is a deliberately separate rendering path from ``assemble_replay``'s ``novel``/``log``
styles (never imported by, or wired into, that module) for two reasons:

1. It needs a ``SessionReconstruction`` — scene boundaries derived from project *state*, not
   just turn artifacts — which ``assemble_replay(runs_dir, style)`` has no way to obtain from a
   bare ``runs_dir`` alone (that's why the CLI passes it in separately; see ``cli/export.py``).
2. It shows **every** roll for a turn, not just rolls reachable from a reader-visible event
   (D121's roll-visibility filter that ``render.py``'s ``log`` style applies). ``--trpg`` is
   explicitly a GM artifact — hiding GM-only rolls/interventions would defeat its purpose — so
   this module intentionally does not reuse ``TurnRecord.reader_visible_rolls``.

Default (no ``--trpg``) replay output is therefore untouched by this module's existence:
``assemble.py``/``render.py``/``loader.py`` are not modified by Issue 028.
"""

from __future__ import annotations

from typing import Any

from living_narrative.export_replay.assemble import NoReplayableTurnsError
from living_narrative.export_replay.loader import TurnRecord
from living_narrative.export_replay.reconstruction import SessionReconstruction, scene_for_turn
from living_narrative.export_replay.render import _GAP_STATUS_LABELS

_HEADER = (
    "# TRPGリプレイ (GM出力)\n\n"
    "このリプレイはGM向けの出力です。ロール・介入を含みます。プレイヤー/reader向け出力とは"
    "別に扱ってください。"
)


def render_trpg_replay(records: list[TurnRecord], reconstruction: SessionReconstruction) -> str:
    """GM-oriented TRPG replay: narration + rolls + interventions per turn, grouped under
    scene headings. Raises ``NoReplayableTurnsError`` under the same condition
    ``assemble_replay`` does (no applied, non-``reject_all`` turn exists yet)."""
    if not any(record.is_body_turn for record in records):
        raise NoReplayableTurnsError(
            "no applied (non-reject_all) turn exists yet — run `turn`/`auto` first"
        )

    blocks = [_HEADER]
    current_scene_id: str | None = None
    for record in records:
        scene = scene_for_turn(reconstruction.scenes, record.turn)
        if scene is not None and scene.id != current_scene_id:
            blocks.append(f"## シーン: {scene.location} ({scene.id})")
            current_scene_id = scene.id
        blocks.append(_turn_block(record) if record.is_body_turn else _gap_block(record))

    return "\n\n".join(blocks).rstrip("\n") + "\n"


def _gap_block(record: TurnRecord) -> str:
    if record.status == "applied":  # reject_all
        return f"### ターン {record.turn} (reject_allにより状態へ反映されず)"
    label = _GAP_STATUS_LABELS.get(record.status or "", record.status or "不明")
    return f"### ターン {record.turn} (未解決: {label})"


def _turn_block(record: TurnRecord) -> str:
    lines = [f"### ターン {record.turn}"]
    if record.rolls:
        lines.append("ロール欄:")
        lines.extend(f"- {_roll_line(roll)}" for roll in record.rolls)
    if record.interventions:
        lines.append("介入欄:")
        lines.extend(
            f"- GM介入: {item.get('type')} — {item.get('content', '')}"
            for item in record.interventions
        )
    lines.append("")
    lines.append(record.narration_body or "")
    return "\n".join(lines)


def _roll_line(roll: dict[str, Any]) -> str:
    label = roll.get("label") or roll.get("type") or "roll"
    notation = (roll.get("dice") or {}).get("notation")
    result = roll.get("result")
    if notation:
        return f"{label}: {notation} → {result}"
    return f"{label}: {result}"
