---
id: 108
title: draft runのplan世代、continuity出典、export path、孤児attemptを直す
status: completed
completed: 2026-08-18
created: 2026-08-18
type: bugfix
priority: P1
parent: 101
blocked_by: []
labels: [long-form, drafting, coordinator, export, lineage]
---

# 108: draft runのplan世代、continuity出典、export path、孤児attemptを直す

## 背景

PR #30 の4巡目レビューで、置換planと部分書込みに関する契約違反が4件残っていることが指摘された。

## 完了条件

- draft run の識別子は現行 BookPlan 世代を含み、置換plan後に旧planのresponseを再開しない。
- 受理時の continuity 要約と covered thread は、著者がレビューした attempt に由来する。
- `export manuscript` は解決済み `workspace.state` を読む。
- `lineage.yaml` 置換前に停止して残った attempt ディレクトリは、再試行で完了できる。
- focused回帰、全test、ruff、format、diff checkを通す。

## 実装結果

- `_plan_generation()` を `plan_generation()` として公開し、`run_chapter_draft()` の `run_id` に含める。`run_id` の決定は lock 内の state snapshot 後に行う。
- 受理経路の ledger diff は `_reviewed_attempt_id()` が解決した attempt から continuity を構築する。accepted pointer と同一 attempt になる。
- `resolve_workspace_dirs()` を公開し、`export_accepted_manuscript()` が `Path` と `WorkspacePaths` の両方を受ける。CLI は `read.paths` を渡す。
- `record_chapter_attempt()` は manifest 未登録の attempt ディレクトリ（部分書込みの残骸）を破棄してから作り直す。

## 検証結果

- focused: drafting / coordinator / exporter / lineage — PASS。
- `NO_COLOR=1 uv run pytest` — 1124 passed / 2 skipped。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。

## 関連ファイル

- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/coordinator.py`
- `src/living_narrative/book/exporter.py`
- `src/living_narrative/book/lineage.py`
- `src/living_narrative/cli/export.py`
- `tests/book/test_drafting.py`
- `tests/book/test_lineage.py`
- `tests/book/test_exporter.py`
- `tests/book/test_chapter_production_coordinator.py`
