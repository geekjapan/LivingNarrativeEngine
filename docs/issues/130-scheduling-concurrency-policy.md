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

## v0.7.0 実装スライス

ADR-0019に従い、queueのBook内lease責務を変更せず、明示設定されたscheduler namespaceにおける`ProductionAdmissionController`を導入する。公開seamは`try_admit(request)`と`release(lease, outcome)`に限定する。

- [ ] 同一scheduler namespace内で異なるBookのactive admission数をconfigured上限以下に保つ。
- [ ] profile IDごとのdurable rate limitを決定的なclock注入テストで検証し、超過jobをterminal failureにせずqueuedのままdeferする。
- [ ] Book hard USD capではactual usage、active reservation、今回estimateを合算し、unknown evidenceをfail closedにする。
- [ ] reservationはcomplete、sanitized failure、admission expiry、queue deferralでfencing generationを検証して安全に解放できる。
- [ ] scheduler namespaceのsnapshot/events/Cockpit metricsはreader-safeであり、本文、prompt、credential、workspace path、worker identity、tracebackを保存・投影しない。
- [ ] scheduler namespace未設定の既存projectはv0.6.0と同じ単一Book queue挙動を維持する。
- [ ] 同一Bookのserial lease、StateDiffによるBook State mutation、明示的な著者accept/reviseを回帰テストで保持する。

## 非対象

v0.7.0では、明示設定されたscheduler namespace内だけで複数Bookを横断するadmission policyを対象にする。暗黙のマシン全体scheduler、外部broker、分散clock同期、provider live quota取得、auto-accept/auto-reviseは対象外である。
