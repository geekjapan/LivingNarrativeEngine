# ADR-0008: project transaction・排他・crash recovery契約

## Context

turn commitは「state前進→inverse_diff書込」の順で、間のcrashは巻き戻し不能なstate前進と
project block(meta欠落)を生む。`StateStore.save`はbundle transactionでなく、OS lockは全経路に
存在せず、turn番号とRNG offsetは都度スキャン導出のため並行実行で衝突する。復旧導線もない(Issue 055)。

## Decision

1. **排他**: project root直下`.lock`への`fcntl.flock(LOCK_EX|LOCK_NB)`。全mutation経路
   (turn/review/rollback/restore/settings/auto-run)で必須、純readはlock不要。既定は
   非ブロッキング即エラー。POSIXのみ(persona=uv/docker)、native Windowsはpost-1.0。
2. **commit journal**: staging dirもDBも導入しない。順序を反転し
   「inverse_diff+commit-intent(`state_hash_before`/`state_hash_after`/`diff_id`/`rng_start_offset`)を
   fsync → `StateStore.save` → meta.yaml(status=applied)=確定marker」とする。
3. **state hash規約**: state bundle全YAMLの正規化連結のsha256。算出規約の変更はmigration対象。
4. **turn identity+RNG pin**: identity=`(turn_number, diff_id)`。turn番号とrng_start_offsetは
   commit-intentへpinし、retryは再スキャンしない。再適用は`hash==hash_before`のときのみ。
5. **recovery分類**: mutation前にlock取得→最新turnを検査。intent有+hash_after一致=meta補完、
   hash_before一致=discard、どちらとも不一致=quarantine(mutation拒否)、intent無=現行discard踏襲。
   pre-β turnは現行「meta欠落=block」を維持。
6. 実装境界は`state/transaction.py`(ADR-0009)。

## Consequences

- meta.yamlへのフィールド追加はartifact schema=公開契約の変更であり、βschema凍結(ADR-0011)前に
  確定する。以後の変更はmigration義務を伴う。
- torn stateは検出・隔離されるが自動修復されない(bundle atomic swapは意図的に作らない)。
- fault injection+multiprocessテストmatrixが本契約の回帰gateとなる。
