---
id: 071
title: 100ターンmock long-run journeyをCI常設gateにする
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 057
blocked_by: [070]
---

# 071: 100ターンmock long-run journeyをCI常設gateにする

Issue 057の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- ADR-0010のjourney(export/snapshot/介入分岐/rollback/backup-restore resume込み)を100ターンmockで自動走行。
- gate SLO閾値(stall≤3、resolved比≥0.5、max_open_turns≤25、leak=0、ceiling≤5、game発火>0)をassert。
- 同一seed 2回実行のreplay完全一致をassert。CIで常設実行される。

## 関連ファイル

- `tests/smoke/`
- `docs/adr/0010-quality-gate-narrative-slo.md`
