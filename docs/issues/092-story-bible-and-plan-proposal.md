---
id: 092
title: Story BibleからreviewableなBookPlan proposalを生成する
status: completed
created: 2026-08-17
type: implementation
priority: P0
parent: 091
blocked_by: [091]
labels: [long-form, planning, cli]
---

# 092: Story BibleからreviewableなBookPlan proposalを生成する

## 背景

ADR-0014によりBookPlanとBookLedgerのcanonical state境界が確定した。次に必要なのは、
作者の意図を検証可能な構造化入力として受け取り、LLM自由文やUI local stateを経由せず、
review可能なStateDiff proposalへ変換することである。

## 完了条件

- Story Bibleがpremise、audience、act、chapter、thread、arc、word rangeを構造化して検証する。
- act/chapter参照・ID一意性の検証はBookPlan schemaと同じ正本ルールを再利用する。
- 同一Story Bibleは同一proposal IDと同一BookPlan/BookLedgerを生成する。
- proposalは`book_plan`（canon）と`book_ledger`（gm_only）の明示的StateDiffへ変換できる。
- `living-narrative book plan`はproposal artifactだけを出力し、canonical stateを変更しない。
- 日本語利用手順を文書化する。

## 実装結果

- `living_narrative.book.planning`にStory Bible、proposal、決定的hash、StateDiff変換を追加した。
- `living-narrative book plan --story-bible <yaml> --output <proposal>`を追加した。
- `docs/long-form-workflow.md`に入力、review、visibility、state更新境界を記録した。
- proposalの直接適用はこのIssueの非目標である。次のbook/chapter coordinatorが既存transaction内で承認済みdiffをcommitする。

## 検証結果

- `NO_COLOR=1 uv run pytest tests/book/test_planning.py tests/cli/test_book_command.py` — 5 passed。
- Story Bibleの空premise、act/chapter不整合、重複IDはschemaでfail-fastする。

## 関連ファイル

- `docs/adr/0014-long-form-book-state-boundary.md`
- `docs/long-form-workflow.md`
- `src/living_narrative/book/planning.py`
- `src/living_narrative/cli/book.py`
- `tests/book/test_planning.py`
- `tests/cli/test_book_command.py`
