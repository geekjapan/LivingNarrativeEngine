---
id: 123
title: Cost Policy v2のADR・料金snapshot・hard/soft capを実装する
status: done
created: 2026-08-21
type: feature
priority: P1
parent: 123
blocked_by: [122]
labels: [long-form, cost, governance, budget]
---

# 123: Cost Policy v2のADR・料金snapshot・hard/soft capを実装する

## 背景

attempt回数による既存budgetだけでは、長編制作におけるtoken/USD消費、profileごとの単価、act/book全体の予算を説明できない。provider呼出し前に見積りを用いてhard stopし、実行後にactual usageへ帰属できる土台を作る必要がある。

## 公開seam

`evaluate_cost_policy(policy, scope_costs, estimate) -> CostPolicyAssessment`を公開seamとする。callerはproviderを呼ぶ前にassessmentを受け取り、`block`の時だけ呼出しを止める。policyは状態を変更せず、著者のaccept/reviseを行わない。

## 完了条件

- [x] `PriceSnapshot`にprofile、version、USD input/output単価、税、割引を持たせる。
- [x] chapter/act/bookのtoken/USD soft/hard capと、deterministicなestimateを評価できる。
- [x] hard cap超過またはhard cap下のunknown price/estimateでprovider呼出しが0回になる。
- [x] soft cap超過はreader-safe warning/evidenceを残し、明示的なproduction実行を阻害しない。
- [x] `Decimal`計算、価格version、unknown usageの扱い、既存attempt budget互換をfocused testで固定する。
- [x] `BookBudgetPolicy`既存callerを破壊しない。

## 非対象

provider responseのactual usage attribution、Cockpit表示、通貨換算、tax invoice、auto-retry/auto-acceptは後続Issueへ分離する。
