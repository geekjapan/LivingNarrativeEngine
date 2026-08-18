---
id: 110
title: 章制作フロー(draft/candidate/review-open)をweb経路へ公開する
status: open
created: 2026-08-18
type: feature
priority: P1
parent: 101
blocked_by: []
labels: [long-form, web, production-runner]
---

# 110: 章制作フロー(draft/candidate/review-open)をweb経路へ公開する

## 背景

現在の Cockpit は `planned → running` と `review → accepted/revising` だけを操作でき、その間の `run_chapter_draft()`、`record_chapter_candidate()`、`open_chapter_review()` に production caller がない。そのため Cockpit から開始した章は、内部Python APIを直接呼ばない限り `running` のまま留まる。

これは PR #30 が「将来の拡張: Production Runner」として明示的に範囲外にした部分であり、LLM呼び出しを伴う長時間処理の実行モデル（同期/非同期、進捗表示、コスト上限、失敗時の再開UI）を決める必要がある。

## 完了条件

- draft 実行、candidate 記録、review open を web もしくは CLI から実行できる。
- 実行モデル（同期/非同期）と進捗・失敗表示を決め、ADRに記録する。
- budget と circuit breaker が web 経路でも適用される。
- 章1本を Cockpit だけで `planned → accepted` まで進められる受入テストを持つ。

## 関連ファイル

- `src/living_narrative/web/app.py`
- `src/living_narrative/web/service.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/coordinator.py`
