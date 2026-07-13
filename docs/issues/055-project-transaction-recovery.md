---
id: 055
title: project更新のtransaction・排他・crash recovery契約を決定する
status: review
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


## 決定案(2026-07-13、承認待ち)

調査による事実確認: turn commitは `StateStore.save`(state前進)→`save_apply_artifacts`(inverse_diff)の順(`driver.py:302-373`)で、その間のcrashは**巻き戻し不能なstate前進**を生む(rollbackはinverse欠落で拒否 `rollback.py:82-92`、meta欠落で次turn実行不能 `turn_numbering.py:61-62`、復旧導線なし)。`StateStore.save`は個別atomic replaceのみでbundle transactionなし(`store.py:126-157`)。`save_apply_artifacts`の`_write_yaml`は非atomic(`diff.py:345-347`)。OS lockは全経路不在(threading.LockはWeb auto-run 1本ガードのみ)。turn番号とRNG offsetは都度スキャン導出のため並行実行で衝突・二重消費し得る。review/rollbackも同じ穴を共有。doctor/repair導線なし。

### 決定

- (a) **lock**: project root直下`.lock`への`fcntl.flock(LOCK_EX|LOCK_NB)`(stdlib、新規依存なし)。全mutation経路(turn/review/rollback/restore/settings/auto-run)で必須、純readはlock不要。既定は非ブロッキング即エラー、`--wait`/`--lock-timeout`はshould。crash時はカーネル自動解放でstale lockなし。POSIXのみ(persona=uv/docker=POSIX full cover)、native Windowsはpost-1.0。
- (b) **journal/marker**: staging dirもDBも導入せず、turn dir=journal recordとして最小拡張。順序を反転し「inverse_diff+commit-intent(`state_hash_before`/`state_hash_after`/`diff_id`/`rng_start_offset`)をfsync → `StateStore.save` → meta.yaml(status=applied)=確定marker」。torn stateはhash検出→quarantine(bundle全体atomic swapは作らない)。
- (c) **idempotent retry**: turn identity=`(turn_number, diff_id)`。turn番号とrng_start_offsetをcommit-intentへpin(再スキャン導出をやめる)。再適用は`hash(state)==hash_before`のときのみ、`==hash_after`ならmeta確定のみ=二重適用をhashで排除。
- (d) **recovery state machine**(mutation実行前、lock取得直後): meta有効=clean続行 / meta無+intent有+hash_after一致=meta補完(auto-recover) / hash_before一致=turn dir discard(auto-recover) / どちらとも不一致=quarantine(mutation拒否、restore/手動repair案内) / intent無=現行discard踏襲。pre-βのhash無しturnは現行「meta欠落=block」を維持(安全側)。
- (e) **test matrix**: fault injection(書込N番目後crash×5注入点→§dの正しい分類をassert)+multiprocess(turn×turn/turn×review/turn×rollback/turn×backupの同時発行→lockで直列化、state交錯・RNG二重消費・turn番号衝突ゼロをassert)。
- (f) 分類: **must**=lock+順序反転+commit marker形式確定(βschema凍結前、公開契約)+RNG-offset pin+recovery中核 / **should**=doctor CLI、--wait、copy/backupのfsync耐久化 / **post-1.0**=Windows lock、DB backend、bundle double-buffer。

### ADR候補(hard-to-reverse)

- **ADR: project transaction・排他・recovery契約** — lock契約(.lock/flock/read非lock/非ブロッキング既定)、commit journal形式(meta.yamlへhash/rng-offsetフィールド追加)、state hash算出規約(sha256+正規化)、recovery分類意味論、turn identity+RNG pin契約を1本で固定。artifact schemaは公開契約のためβschema凍結(059)・044と連動して確定必須。

### 実装Issue分割

- A(must中核): lock+journal/hash+順序反転+save_apply_artifacts atomic化(driver/review/rollback全経路、migration連携サブタスク込み)
- B(must+should): recovery state machine + doctor CLI
- C(gate): fault injection+multiprocessテストmatrix(A/Bに依存)

### 未解決(実装前確認)

- `_discarded_` dirのrollsがRNG会計に計上されるか(`pipeline/rng_state.py`) — retryが「新RNG消費」か「同一roll再生」かの現契約確定
- serveの複数uvicorn worker許容有無(単一worker前提なら非ブロッキング即エラーで十分)
