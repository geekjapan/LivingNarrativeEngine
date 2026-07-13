---
id: 066
title: state/transaction.pyを新設しlock+commit journal+順序反転を全state変更経路へ統合する
status: done
created: 2026-07-13
type: implementation
priority: P0
parent: 055
blocked_by: []
---

# 066: state/transaction.pyを新設しlock+commit journal+順序反転を全state変更経路へ統合する

Issue 055の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- `state/transaction.py`に`project_lock()`(flock LOCK_EX|LOCK_NB、`.lock`)/`commit_state_diff()`/`classify_recovery_state()`を実装。
- commit順序を反転: inverse_diff+commit-intent(state_hash_before/after、diff_id、rng_start_offset)fsync→`StateStore.save`→meta.yaml確定。
- `driver.py` commit phaseと`session/review.py`・`session/rollback.py`が同一APIを使用(重複解消)。
- `save_apply_artifacts`のatomic化。meta.yamlへの追加フィールドをschema/migration(044)と整合させる。
- 順序反転なしで失敗するregression test(state前進+inverse欠落の再現)を含む。
- GitNexus impact report確認(cross-module)。

## 関連ファイル

- `src/living_narrative/pipeline/driver.py`
- `src/living_narrative/state/store.py`、`src/living_narrative/state/diff.py`
- `src/living_narrative/session/review.py`、`src/living_narrative/session/rollback.py`
- `docs/adr/0008-project-transaction-recovery.md`、`docs/adr/0009-v1-architecture-debt-scope.md`
