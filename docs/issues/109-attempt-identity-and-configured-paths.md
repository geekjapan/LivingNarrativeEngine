---
id: 109
title: attempt identityと再試行入力、benchmark pathを直す
status: completed
completed: 2026-08-18
created: 2026-08-18
type: bugfix
priority: P1
parent: 101
blocked_by: []
labels: [long-form, lineage, drafting, benchmark]
---

# 109: attempt identityと再試行入力、benchmark pathを直す

## 背景

PR #30 の5巡目レビューで、attempt の同一性判定と再試行時の入力保持、benchmark の workspace path に関する契約違反が指摘された。

## 完了条件

- attempt の同一性は candidate 本文だけでなく review と `draft_run_id` を含む。同一本文でも review が変われば新しい attempt を記録する。
- 受理対象の attempt は現在の review に一致するものを優先して解決する。
- 同一 attempt の再試行は永続化済み `request.yaml` / `prompt.yaml` を再利用し、上書きしない。
- `benchmark_book()` は解決済み `workspace.state` を読む。
- focused回帰、全test、ruff、format、diff checkを通す。

## 実装結果

- `record_chapter_attempt()` の重複拒否条件を (candidate hash, review, `draft_run_id`) の一致に変更した。coordinator の記録判定も同じ tuple を使う。
- `_reviewed_attempt_id()` は現在の `review.yaml` に一致する attempt を優先し、なければ本文一致の最新を選ぶ。
- `run_chapter_draft()` は `request.yaml` と `prompt.yaml` が揃っていれば永続化済み prompt から messages を復元する。
- `benchmark_book()` は `Path` と `WorkspacePaths` の両方を受ける。

## 検証結果

- focused: lineage / coordinator / drafting / benchmark — PASS。
- `NO_COLOR=1 uv run pytest` — 1127 passed / 2 skipped。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。

## 関連ファイル

- `src/living_narrative/book/lineage.py`
- `src/living_narrative/book/coordinator.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/benchmark.py`
- `tests/book/test_lineage.py`
- `tests/book/test_drafting.py`
- `tests/book/test_benchmark.py`
