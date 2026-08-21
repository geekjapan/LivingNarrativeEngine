---
id: 130
title: Chapter ProductionのScheduling/Concurrency Policyを実装する
status: in-progress
created: 2026-08-21
type: feature
priority: P1
parent: 130
blocked_by: [129]
labels: [long-form, production, scheduling, concurrency]
---

# 130: Chapter ProductionのScheduling/Concurrency Policyを実装する

## 背景

BookPlanのchapter順序、continuity context、chapter lifecycleを安全に保つには、複数workerが存在しても同じBook内で同時に複数chapterを制作してはならない。一方、異なるBook間のparallelismはprovider rate limitとbudget reservationを考慮して後続で導入する。

## 公開seam

`DurableProductionQueue.claim(project_yaml, worker_id)`がbook内serialの制御点である。queued jobが複数あっても、active leaseがあれば別chapterのclaimを返さない。expired leaseはjob lockを獲得できた時だけ同じjobを再claimする。

## 完了条件

- [x] 同一workspace/Bookで同時にleaseできるdelivery jobを常に一件に制限する。
- [x] active lease中に別chapterのqueued jobをclaimしない。
- [x] completed deliveryのjob lock解放後、次chapterをclaimできる。
- [x] expired jobがある場合に別chapterへ追い越さず、同じjobのsafe resumeを優先する。
- [x] coordinator既存のBook lifecycle serial guardを残し、queueを唯一の防御にしない。
- [ ] book間parallel上限、provider profileごとのrate limit、USD budget reservationをpolicy modelとintegration testで実装する。

## 非対象

このIssueの現スライスは単一Bookの順序・二重実行防止のみを対象にする。複数workspaceを横断するglobal scheduler、外部broker、auto-accept/auto-reviseは対象外である。
