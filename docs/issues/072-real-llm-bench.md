---
id: 072
title: 実LLM30ターンbench手順とbenchmark artifact形式を整備する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 057
blocked_by: [070]
---

# 072: 実LLM30ターンbench手順とbenchmark artifact形式を整備する

Issue 057の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- sandbox実行手順(コマンド・seed・provider設定)を文書化し、JSON+`docs/evaluations/`のmarkdown転記形式を固定する。
- provider failureのfail扱い+発生turn記録を含む。
- β/1.0 gate時の実行手順としてrubric(073)と接続する。転記半自動CLIはshould。

## 関連ファイル

- `docs/evaluations/`
- `docs/adr/0010-quality-gate-narrative-slo.md`
