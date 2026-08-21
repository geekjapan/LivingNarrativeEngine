---
id: 124
title: provider usageをrun・attempt・act・bookへ帰属する
status: done
created: 2026-08-21
type: feature
priority: P1
parent: 123
blocked_by: [123]
labels: [long-form, cost, usage, reporting]
---

# 124: provider usageをrun・attempt・act・bookへ帰属する

## 背景

Cost Policy v2がprovider呼出し前のestimateを扱うためには、実行後のactual usageを監査可能なscopeへ集計し、estimateとの差分を後続reportで比較できなければならない。集計に本文、prompt、credential、private/GM dataを含めないことが前提である。

## 公開seam

`collect_book_usage(project_yaml, price_snapshot=...) -> BookUsageSummary`をread-only seamとする。draft runのdurableな`request.yaml`と`calls.yaml`だけから、run/attempt/chapter/act/book/stageへtokenとactual USDを帰属する。

## 完了条件

- [x] durable draft callをrun・attempt・chapter・act・book・stageへreader-safeに集計する。
- [x] input/output/total tokenとactual USDを`Decimal`で集計する。
- [x] request/calls欠落または未知tokenのrunを成功actualへ合算しない。
- [x] 不完全runをunattributed evidenceとして一覧化する。
- [x] price version、actual/estimate差分、scope別forecastを後続Cockpit/reportへ投影できる。

## 非対象

provider APIへの追加問い合わせ、本文/promptの保存、モデル別課金の推測、税務報告は本Issueに含めない。
