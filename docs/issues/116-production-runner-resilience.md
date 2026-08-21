---
id: 116
title: Production Runnerのfault injection・budget・recoveryを検証する
status: closed
created: 2026-08-21
type: quality
priority: P1
parent: 110
blocked_by: [112, 114]
labels: [long-form, resilience, testing]
---

# 116: Production Runnerのfault injection・budget・recoveryを検証する

## 実装内容

Production Runnerの境界失敗をTDDで検証した。budget policyによるprovider呼出し前block、保存済みresponseのproviderなしresume、phase-boundary stop、provider例外のsanitized failure、review lifecycleとmanifestの矛盾、同一本文revisionのtransaction provenanceを対象にする。

provider failureの詳細文字列は同期CLI callerへ伝播し得るが、durable run artifactおよびWeb/CLIのstatus projectionには例外class由来のfailure codeだけを保存・表示する。成功resume後には過去のfailure artifactを診断履歴として残しても、current statusのfailure codeを解消済みとして扱う。

## 完了条件

- [x] budget blockでproviderを呼ばず`stopped`を返す。
- [x] budget stopされたrevising runを同じartifactからresumeできる。
- [x] provider failure artifactにcredential、path、prompt、本文が入らない。
- [x] failure後の成功resumeは`awaiting_author`を返しcurrent failure codeを残さない。
- [x] manifest/lifecycle矛盾はprovider呼出し前に`failed`へ記録する。
- [x] 同一本文・異なるdraft provenanceがcandidate/review transactionを衝突させない。

## 主な検証

`tests/book/test_production_runner.py`のfault-injectionケース、`tests/book/test_chapter_production_coordinator.py`、`tests/book/test_lineage.py`で確認する。
