---
id: 125
title: Budget Cockpitとreader-safeなforecast・停止条件を実装する
status: done
created: 2026-08-21
type: feature
priority: P1
parent: 123
blocked_by: [123, 124]
labels: [long-form, cost, cockpit, web]
---

# 125: Budget Cockpitとreader-safeなforecast・停止条件を実装する

## 背景

著者は章制作を開始する前に、actual usage、保存済みestimate、hard cap残額、hard stop後にresume可能かを確認できる必要がある。金額表示はprompt、本文、credential、provider requestなどを含まないreader-safe projectionであることが必要である。

## 公開seam

既存の`GET /api/project/{name}/book/cockpit`へ`budget`をオプションで投影する。`budget`はstatus、reason、price version、actual/estimate/variance/forecast、hard残額、resume可否だけを持つ。`POST .../run`は`resume_allowed=false`の時に409を返し、UIでのボタン非表示だけに依存しない。

## 完了条件

- [x] configured policyのbook scopeをCockpit APIと画面に表示する。
- [x] actual/estimate/variance/hard残額をDecimal由来でreader-safeに表示する。
- [x] 未価格・未知usageでhard capを評価できない時、resumeをfail-closedにする。
- [x] UIはhard stop時に章制作/再開操作を提示しない。
- [x] serverはhard stop時の`run`要求を409で拒否する。
- [x] 本文、prompt、credential、absolute path、GM/private dataをAPI/HTMLへ含めない。

## 非対象

金額の自動調整、著者の代わりのbudget変更、auto-retry、auto-accept、通貨換算は含めない。
