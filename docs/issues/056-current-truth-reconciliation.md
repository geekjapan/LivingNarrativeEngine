---
id: 056
title: Issue・計画・実装のcurrent truthを再同期する
status: open
created: 2026-07-12
type: wayfinder:research
priority: P0
parent: 052
blocked_by: []
---

# 056: Issue・計画・実装のcurrent truthを再同期する

## 問い

Issue 001〜051、完了済みDAG、凍結spec、企画書、README、現行code/testの矛盾と未証明条件をどう分類し、どの文書を現行仕様索引・歴史資料・将来ビジョンとして扱うか。

## 背景

全Issueは`done`だが、Issue 016の実LLM確認、Issue 038の`in_progress`記述、transition count、thread resolve、rollback RNG等に検証負債がある。`feature-dag-e7-e9.md`は途中時点のままで、`spec-foundation.md`と`project_plan.md`には実装済み機能を非目標とする歴史記述が残る。READMEも主要commandへの導線が不足する。

## 解決条件

- stale、historical、current、unverifiedを全関連文書で分類する
- 未チェック条件と既知制限をrelease blocker／品質改善／明示的非目標に分ける
- 現行仕様索引の置き場所と更新責任を決める
- α／β／1.0判定表へ根拠リンクを付ける
- 文書修正を小さな実装Issueへ切れる状態にする

## 関連ファイル

- `docs/issues/`
- `docs/plan/`
- `docs/spec-foundation.md`
- `docs/project_plan.md`
- `docs/session-autonomy.md`
- `docs/intervention.md`
- `README.md`

