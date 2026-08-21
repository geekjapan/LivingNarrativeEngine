---
id: 112
title: Domain Production Runnerとdurable manifest/eventsを実装する
status: closed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [111]
labels: [long-form, production-runner, recovery]
---

# 112: Domain Production Runnerとdurable manifest/eventsを実装する

## 実装内容

`book.production_runner.ChapterProductionRunner`を追加し、`planned`または`revising`の章を、既存のcoordinator、recoverable draft、semantic continuity review、immutable lineageへ順に委譲する。RunnerはBook Ledgerを直接更新せず、既存のStateDiff transactionだけを通して`running`、`candidate`、`review`へ遷移させる。

run artifactは`runs/chapter_production/<chapter-id>/generation_<generation>_revision_<ordinal>/`に保存する。eventを先にatomic writeしてからmanifestを更新し、`request.yaml`、`manifest.yaml`、`links.yaml`、停止・失敗artifactには本文、prompt、credential、absolute path、GM-only dataを保存しない。

## 完了条件

- [x] planned/revisingからdraft、candidate、reviewを経て`awaiting_author`へ到達する。
- [x] 保存済みdraft responseをprovider再呼出しせずに再利用する。
- [x] draft前、draft後、candidate記録後にdurable stop requestをphase boundaryで適用する。
- [x] budget blockをprovider failureではなく再開可能な`stopped`へ写像する。
- [x] manifest/lifecycle矛盾をprovider前にfail closedし、sanitized failure codeだけを公開する。
- [x] provider failure後、同一runを再開してcurrent failure statusを解消できる。
- [x] 同一本文でも異なるdraft provenanceを持つrevisionを別attempt・別transactionとして扱う。

## 主な検証

`tests/book/test_production_runner.py`はhappy path、response reuse、phase-boundary stop、budget block/resume、manifest矛盾、provider failure/recoveryを検証する。`tests/book/test_chapter_production_coordinator.py`および`tests/book/test_lineage.py`はprovenanceを含むtransaction key変更の回帰を検証する。
