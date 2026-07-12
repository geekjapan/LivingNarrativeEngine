---
id: 055
title: project更新のtransaction・排他・crash recovery契約を決定する
status: open
created: 2026-07-12
type: wayfinder:prototype
priority: P0
parent: 052
blocked_by: []
---

# 055: project更新のtransaction・排他・crash recovery契約を決定する

## 問い

turn、review、rollback、settings、migration、backup/restoreが同一projectを更新するとき、process crashや同時実行後も「state、artifact、metaが同じcommitを指す」ことをどう保証し、どの状態を自動復旧／quarantine／手動repairするか。

## 背景

現行turn commitは`StateStore.save`後にinverse diff、state diff、history、metaを書くため、後半失敗時に`failed` artifactと進んだstateが共存し得る。`StateStore.save`もbundle約15ファイルを個別atomic replaceするだけでbundle transactionではない。OS-level project lockがなく、CLI/Web/multiprocess mutationも競合し得る。missing/unparseable `meta.yaml`を直す`doctor`導線もない。

## 解決条件

- project-scoped OS file lockの所有範囲・timeout・read/write方針を決める
- staged state directory、journal、before/after hash、commit markerのprotocolを決める
- retryをidempotentにするturn identityとRNG契約を決める
- startup／command実行時のrecovery state machineを決める
- fault injectionとmultiprocess test matrixを定義する
- hard-to-reverseな判断をADR候補として明示する

## 関連ファイル

- `src/living_narrative/pipeline/driver.py`
- `src/living_narrative/state/store.py`
- `src/living_narrative/session/review.py`
- `src/living_narrative/session/rollback.py`
- `src/living_narrative/pipeline/turn_numbering.py`
- `src/living_narrative/web/service.py`
- `tests/pipeline/test_failure_handling.py`

