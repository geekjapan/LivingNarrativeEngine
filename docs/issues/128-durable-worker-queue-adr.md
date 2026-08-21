---
id: 128
title: Durable Production Queue/WorkerのADR・耐久性境界を定義する
status: in-progress
created: 2026-08-21
type: feature
priority: P1
parent: 128
blocked_by: [127]
labels: [long-form, production, durability, queue, worker]
---

# 128: Durable Production Queue/WorkerのADR・耐久性境界を定義する

## 背景

Webのin-process background adapterは、HTTP requestから章制作を分離しているが、process停止後に実行者を維持しない。v0.6.0では、100章規模の長編制作を予約・停止・再開・監視できるdurable execution substrateへ段階的に移行する。

## 公開seam

`DurableProductionQueue.enqueue(project_yaml, chapter_id)`、`DurableProductionQueue.status(project_yaml, chapter_id)`、`DurableProductionWorker.run_once(project_yaml, worker_id)`を公開seamとする。workerは既存`ChapterProductionRunner`を呼ぶだけで、Book State mutation、著者のaccept/revise、本文生成の再実装を行わない。

## 完了条件

- [x] backend、durability、lease、retention、failure domainをADR-0018に決定する。
- [x] queue payloadから本文、prompt、credential、GM/private context、absolute pathを排除する。
- [x] idempotency key、job lock、renewable lease、at-least-once deliveryの責務を既存Runnerのrun identityと分離する。
- [x] lease expiry単独で同時Runnerを生まない設計を固定する。
- [x] worker kill、lease expiry、provider timeout、partial writeをfault injection対象と明記する。
- [x] Book lifecycleがCoordinator/StateDiffの正本であり、queueがrepair sourceではないことを明記する。

## 非対象

book内serial・book間parallel・provider rate limit・budget reservationはIssue 130、100章index/SLOはIssue 131、metrics/alert/runbookはIssue 132で扱う。外部brokerまたは異なるhost間の共有queueは、adapterが複数必要になるまで導入しない。
