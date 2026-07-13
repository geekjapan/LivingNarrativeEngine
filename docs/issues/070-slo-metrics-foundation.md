---
id: 070
title: SLO測定基盤: metrics拡張+transition論理定義修正+rollback-RNG結合testを実装する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 057
blocked_by: [066]
---

# 070: SLO測定基盤: metrics拡張+transition論理定義修正+rollback-RNG結合testを実装する

Issue 057の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- scene transitionを「旧+新statusペア1組=1遷移」で計数するようmetrics.pyを修正し、既存test期待値を更新する。
- replay一致率・thread resolved比・severity別leak集計をmetricsへ追加する。
- rollback→次turn実行でroll列一致をassertする結合testを追加する(この変更なしでは存在しない保証)。

## 関連ファイル

- `src/living_narrative/session/metrics.py`
- `tests/cli/test_rollback_branch.py`、`tests/session/test_metrics.py`
- `docs/adr/0010-quality-gate-narrative-slo.md`
