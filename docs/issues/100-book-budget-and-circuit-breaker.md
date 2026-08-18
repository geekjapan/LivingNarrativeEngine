---
id: 100
title: Book BudgetとCircuit Breaker
status: in_progress
created: 2026-08-18
---

# Book BudgetとCircuit Breaker

## 背景

長編のretryと改稿は無制限にLLM費用を消費しうる。費用・試行回数・連続quality failureを章とbookの両方で判定し、停止理由を永続化して安全に再開できる必要がある。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| chapter/bookの試行数・token・任意のUSD上限を設定できる | policy schema test |
| draft開始前にbudgetを決定的に評価できる | preflight test |
| 上限超過はprovider呼出し前にblockし、理由を保存する | circuit-breaker test |
| quality revisionの連続上限を超えると停止する | revision failure test |
| BookCockpitにreader-safeなbudget statusと停止理由を投影する | projection/API test |
| 未価格モデルでは確定USDではなくtoken上限のみで判定する | accounting test |

## 関連ファイル

- `src/living_narrative/book/budget.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/cockpit.py`
- `src/living_narrative/llm/costs.py`
- `tests/book/test_budget.py`

## 非対象

外部決済、実課金の制御、provider側quotaの変更は扱わない。
