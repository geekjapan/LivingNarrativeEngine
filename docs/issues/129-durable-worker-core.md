---
id: 129
title: Durable Worker Coreを実装する
status: in-progress
created: 2026-08-21
type: feature
priority: P1
parent: 129
blocked_by: [128]
labels: [long-form, production, durability, queue, worker]
---

# 129: Durable Worker Coreを実装する

## 背景

chapter productionをHTTP processから分離し、worker kill、lease expiry、provider timeout、partial queue writeがあっても、既存Runnerの同一run recoveryを利用して安全に再配送する必要がある。

## 公開seam

`DurableProductionQueue.enqueue(project_yaml, chapter_id)`、`status(project_yaml, chapter_id)`、`heartbeat(project_yaml, claim)`、`DurableProductionWorker.run_once(project_yaml, worker_id)`を公開seamとする。queue snapshotは`runs/chapter_production_queue/queue.yaml`、eventはappend-only artifactとして保存する。

## 完了条件

- [x] queue snapshotをatomic replace + directory fsyncで保存し、schema不正時はfail closedする。
- [x] generation/chapter/revision idempotency keyにより、同じ未完了deliveryを重複enqueueしない。
- [x] POSIX job lockとleaseを併用し、worker kill後のlock解放とlease expiry後にだけ再deliveryできる。
- [x] Runner実行中はheartbeatでleaseを更新し、completion/failure publish前にheartbeatを停止して排他競合を回避する。
- [x] provider timeoutなどのsanitized failureはjobへ記録し、著者またはWeb callerの明示enqueueで同じjob IDをretryできる。
- [x] queued状態のstopはRunner起動前に記録し、同じidempotency keyで再開できる。
- [x] 本文、prompt、credential、absolute path、GM/private context、tracebackをqueue job/event/statusに保存しない。
- [x] focused fault/contract testsでidempotency、retry、lease renewal、worker completion、queued stopを固定する。

## 非対象

book間parallel上限、provider rate limit、budget reservationはIssue 130、100章artifact index/SLOはIssue 131、metric/alert/runbookはIssue 132で扱う。queue自体はBook Stateを変更せず、Runner/Coordinatorを通じたStateDiff transactionを迂回しない。
