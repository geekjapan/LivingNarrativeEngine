---
id: 060
title: 1.0前に解消するarchitecture debtの範囲を決定する
status: open
created: 2026-07-12
type: wayfinder:research
priority: P1
parent: 052
blocked_by: [055]
---

# 060: 1.0前に解消するarchitecture debtの範囲を決定する

## 問い

transaction/recovery契約を実装しやすくし、今後の変更リスクを下げるために、import cycleと責務集中のどこまでを1.0前に分割し、どこを計測付きでpost-1.0へ送るか。

## 背景

GitNexusは`character→llm_gateway→plugins→pipeline registry→agent slots→character`と`character consistency checker↔safety registry`の2 cycleを検出した。`state_manager.py` 899行、`web/service.py` 792行、`web/page.py` 746行、`TurnPipeline.run`約280行に責務が集中する。ただし全面refactorはrelease riskになり得る。

## 解決条件

- transaction coordinatorを置くmodule境界を決める
- import cycleを解く依存方向を決める
- state reducer、web job coordinator、UI分割のrelease blocker範囲を決める
- refactor前後のbehavior／impact／performance検証を決める
- 削除・抽出・延期を優先順位つきで記録する

## 関連ファイル

- `src/living_narrative/pipeline/driver.py`
- `src/living_narrative/agents/state_manager.py`
- `src/living_narrative/web/service.py`
- `src/living_narrative/web/page.py`
- `src/living_narrative/plugins/sdk.py`
- `src/living_narrative/safety/registry.py`

