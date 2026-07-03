"""``novel``/``log`` replay rendering (export-replay/spec.md, both styles deterministic —
no LLM calls, no wall-clock/random content)."""

from living_narrative.export_replay.loader import TurnRecord

_GAP_STATUS_LABELS = {
    "pending_review": "レビュー待ち",
    "stopped_for_review": "レビューのため停止",
    "failed": "失敗",
}


def render_novel(records: list[TurnRecord]) -> str:
    """Prose only: gap turns are omitted with no placeholder (export-replay/spec.md
    "logスタイル出力" Scenario "未解決ターンの省略")."""
    bodies = [record.narration_body or "" for record in records if record.is_body_turn]
    return "\n\n".join(bodies).rstrip("\n") + "\n"


def _gap_placeholder(record: TurnRecord) -> str:
    if record.status == "applied":  # reject_all
        return f"## ターン {record.turn} (reject_allにより状態へ反映されず)"
    label = _GAP_STATUS_LABELS.get(record.status or "", record.status or "不明")
    return f"## ターン {record.turn} (未解決: {label})"


def _intervention_lines(record: TurnRecord) -> list[str]:
    lines = []
    for item in record.interventions:
        target = item.get("target") or {}
        target_desc = target.get("kind", "")
        if target.get("id"):
            target_desc = f"{target_desc}:{target['id']}"
        lines.append(f"- 介入: {item.get('type')} ({target_desc}): {item.get('content', '')}")
    return lines


def _roll_lines(record: TurnRecord) -> list[str]:
    lines = []
    for roll in record.reader_visible_rolls:
        lines.append(f"- ロール: {roll.get('type')} -> {roll.get('result')}")
    return lines


def _diff_lines(record: TurnRecord) -> list[str]:
    if not record.diff or not record.diff.get("applied"):
        return []
    changes = (record.diff.get("diff") or {}).get("changes") or []
    lines = []
    for change in changes:
        target = change.get("target")
        target_id = change.get("id")
        locator = f"{target}.{target_id}" if target_id else target
        path = change.get("path") or "(root)"
        lines.append(f"- 適用diff: {locator}.{path}: {change.get('op')} {change.get('value')}")
    return lines


def _body_block(record: TurnRecord) -> str:
    lines = [f"## ターン {record.turn}"]
    lines.extend(_intervention_lines(record))
    lines.extend(_roll_lines(record))
    lines.extend(_diff_lines(record))
    lines.append("")
    lines.append(record.narration_body or "")
    return "\n".join(lines)


def render_log(records: list[TurnRecord]) -> str:
    blocks = [
        _body_block(record) if record.is_body_turn else _gap_placeholder(record)
        for record in records
    ]
    return "\n\n".join(blocks).rstrip("\n") + "\n"


RENDERERS = {"novel": render_novel, "log": render_log}
