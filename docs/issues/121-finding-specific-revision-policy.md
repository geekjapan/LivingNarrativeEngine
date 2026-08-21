---
id: 121
title: finding別revision policyとlineage決定記録を追加する
status: completed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [119, 120]
labels: [long-form, quality, revision, lineage]
---

# 121: finding別revision policyとlineage決定記録を追加する

## 背景

Semantic Gate v2のfindingは、修正が必要な理由をreader-safe evidenceとして記録できる。しかし、著者が改稿に進む際には、局所改稿、chapter planの再計画、act設計の見直しのどれが最小で妥当な修復範囲かを一貫して説明できなければならない。

## 設計

`decide_revision_policy(review) -> RevisionPolicyDecision`を唯一の公開seamとする。policyはreview artifact内のreader-safe findingだけを入力に取り、findingごとの推奨actionと、優先度に基づく章全体のactionを返す。policy自体は状態遷移を実行せず、acceptもしない。従って、`requires_author_action`が真でも、著者は既存の明示的なaccept/reviseフローで意思決定する。

| finding category | revision action | 理由 |
|---|---|---|
| `point_of_view`、`character_relation`、`foreshadowing`、`other` | `part_revise` | 現行chapter本文内でreader-facing表現を修復できる。 |
| `required_thread`、`character_arc` | `replan` | BookPlan obligationをchapterの設計へ戻して再配置する必要がある。 |
| `act_promise` | `act_redesign` | act全体の約束とchapter目的の整合を再検討する必要がある。 |

## 完了条件

- [x] categoryから`part_revise`、`replan`、`act_redesign`を決定するdeterministic policyを導入した。
- [x] severityが`block`のfindingを含む場合、著者アクションが必要であることを明示した。
- [x] revise reviewを伴うattemptにpolicy decisionをimmutable lineage artifactとして保存した。
- [x] 既存のaccept/revise lifecycleを変更せず、auto-acceptを導入しなかった。
- [x] policy優先度、warnの扱い、lineage再読込をfocused testで固定した。

## 非対象

モデルによる自動改稿、著者の意思決定の代行、actを跨ぐ状態変更は本Issueに含めない。
