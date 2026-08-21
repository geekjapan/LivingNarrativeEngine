---
id: 120
title: Act・arc・characterのreader-safe階層summaryを追加する
status: completed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [119]
labels: [long-form, continuity, summary, quality]
---

# 120: Act・arc・characterのreader-safe階層summaryを追加する

## 背景

既存continuity ledgerはaccepted chapterのbounded digestとopen threadを保持する。30章規模では、次章のcontextへ全chapterの要約を直列投入するだけでは、actのpromise、character arc、重要threadの履歴を同じpriorityで扱えず、context budgetと品質根拠の両方が悪化する。

## 完了条件

- [x] accepted chapter transitionがchapter digestに加え、act summaryとcharacter arc ledgerをtransactionally更新する。
- [x] 全summaryはcandidate本文と既存reader-safe BookPlan/continuity artifactだけから決定的に導出される。
- [x] next chapterのcontextはcurrent act summary、open thread、関連character arc、bounded recent chapter digestを決定的な予算で投影する。
- [x] `render_continuity_digest()`の既存contractを保ち、階層projectionは新しいdeep seamに閉じ込める。
- [x] duplicate accepted chapter、recovery journal、revising、legacy ledgerに対する回帰を追加する。

## 非対象

LLMでsummaryを生成すること、private/GM dataをsummaryに含めること、actを跨ぐ自動replanは本Issueに含めない。
