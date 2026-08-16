---
id: 091
title: BookPlanとBookLedgerのstate境界を導入する
status: completed
created: 2026-08-17
type: implementation
priority: P0
parent: 088
blocked_by: []
labels: [long-form, state, migration]
---

# 091: BookPlanとBookLedgerのstate境界を導入する

## 背景

ADR-0014は、長編制作に必要な作者意図と運用状態を、既存のWorld State、event、
StateDiffと二重化せずに扱うための境界を定義する。現在のstate bundleにはbook planと
chapter lifecycleがなく、周辺ツールの独自stateを取り込むとtransaction、recovery、
rollback、backup/restoreを回避してしまう。

## 完了条件

- `BookPlanState` と `BookLedgerState` がPydantic schemaとして定義される。
- `book_plan.yaml` と `book_ledger.yaml` がStateStoreのload/save/hash対象となる。
- v1 projectは欠落したbook fileを空stateとしてloadできる。新規projectは両fileを作成する。
- `StateDiff` が `book_plan` / `book_ledger` targetを扱い、inverse diffとrollbackを保持する。
- chapter lifecycleは不正遷移を拒否し、計画のchapter ID重複・act参照不整合をfail-fastする。
- schema versionは2へ上がり、v1→v2のproject config migration、fixture、backup/restore、
  transaction recovery regressionが追加される。
- book stateの更新は直接YAMLではなくStateDiff/transactionを通すことをfocused integration testで示す。

## 関連ファイル

- `docs/adr/0014-long-form-book-state-boundary.md`
- `src/living_narrative/state/models.py`
- `src/living_narrative/state/diff.py`
- `src/living_narrative/state/store.py`
- `src/living_narrative/state/transaction.py`
- `src/living_narrative/workspace/layout.py`
- `src/living_narrative/workspace/init.py`
- `src/living_narrative/workspace/migrations.py`
- `tests/test_state_model.py`
- `tests/test_state_transaction.py`
- `tests/workspace/`

## 実装結果

- ADR-0014を追加し、BookPlan（作者意図）、BookLedger（章運用）、World State/Event（実績）、chapter artifact（派生物）の正本境界を固定した。
- `BookPlanState`、`BookLedgerState`、chapter lifecycle、act/chapter/arc/word-range schemaを追加した。
- `StateStore`、state hash、transaction/recovery、backup/restoreに`book_plan.yaml`と`book_ledger.yaml`を参加させた。
- `StateDiff`は`book_plan`（canon）と`book_ledger`（gm_only）のroot setを検証・inverse rollbackできる。
- schema versionを2に上げ、v1→v2 migration、新規projectのempty book file materialization、既存backup manifestの期待値を更新した。

## 検証結果

- `NO_COLOR=1 uv run pytest tests/test_book_state.py tests/test_state_model.py tests/test_state_transaction.py tests/workspace/test_schema_version_loading.py tests/workspace/test_migrations.py tests/workspace/test_beta_schema_fixture.py` — 129 passed。
- `NO_COLOR=1 uv run pytest` — 1073 passed、2 skipped、237.41秒。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。
- GitNexus impact reportは依存パッケージの対話的build承認を要求し、non-interactive実行でも完走できなかった。変更対象はstate transaction boundaryとworkspace migrationであり、focused/full regressionで代替確認した。

## 検証計画

1. public state/schema seamとしてBookPlan、BookLedger、StateDiffをunit testする。
2. StateStore roundtrip、StateDiff apply/inverse/rollback、transaction crash recoveryをtestする。
3. v1 fixtureと新規v2 projectをloadし、migrationとempty book stateの互換をtestする。
4. backup/restore、branch/rollback、full test、ruff、format、diff checkを実行する。
