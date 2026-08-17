---
id: 094
title: Book proposalをtransactionで適用しchapter artifactを永続化する
status: completed
created: 2026-08-17
type: implementation
priority: P0
parent: 093
blocked_by: [091, 092, 093]
labels: [long-form, transaction, artifacts]
---

# 094: Book proposalをtransactionで適用しchapter artifactを永続化する

## 実装結果

- `apply_book_plan_proposal()` を追加した。proposalはworkspace lockを取得し、`runs/.transactions/<proposal_id>/`にproposal、StateDiff、inverse diff、apply report、commit intent、metaを記録した後、既存のjournal-before-state transactionでBookPlan/BookLedgerを更新する。
- 完了済みjournalの再適用は既存commit intentを再利用する。unsafeな中断journalはrecovery errorとして停止し、状態を上書きしない。
- `save_chapter_artifacts()` と `load_chapter_artifacts()` を追加した。candidate Markdown、source-turn provenance、reviewを個別atomic writeで保存し、部分artifactでは復元時にfail-fastする。

## 検証結果

| 検証 | 結果 |
|---|---:|
| book + transaction + backup focused tests | 44 passed / 0 failed |
| 全回帰 `NO_COLOR=1 uv run pytest` | 1089 passed / 2 skipped / 223.84秒 |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS（266 files） |
| `git diff --check` | PASS |

## 次の統合点

このIssueはbook artifactをdurableにしたが、candidateの生成・review decisionからBookLedger lifecycleを実際に更新するchapter coordinator、Web review画面、manuscript/exporter、長編benchmarkは後続の実装単位とする。
