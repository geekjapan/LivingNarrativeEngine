---
id: 107
title: attempt選択・workspace path・lock順・原稿scaffolding・UI権限を直す
status: completed
completed: 2026-08-18
created: 2026-08-18
type: bugfix
priority: P1
parent: 101
blocked_by: []
labels: [long-form, coordinator, drafting, export, web]
---

# 107: attempt選択・workspace path・lock順・原稿scaffolding・UI権限を直す

## 背景

PR #30 の3巡目レビューで、長編制作経路にさらに6件の契約違反が指摘された。いずれも監査可能性、workspace設定の尊重、reader-safe出力という既存契約に対する違反である。

## 完了条件

- 受理は「著者がレビューした候補」に対応する attempt を選ぶ（lineage の末尾ではない）。
- 章の attempt は生成元 draft run を `draft_run_id` として保持できる。
- coordinator は解決済み `workspace.state` / `workspace.runs` を受け取れる。web mutation はそれを渡す。
- draft は project lock を取ってから state snapshot を読む。
- 出荷原稿は narration のみを含み、frontmatter・生成見出し・`> Planned goal:` を含めない。
- Cockpit UI は authoring mode 以外に制作操作を表示しない。
- focused回帰、全test、ruff、format、diff checkを通す。

## 実装結果

- `_reviewed_attempt_id()` を追加し、`candidate.md` の hash に一致する attempt を受理対象にする。一致がなければ従来どおり最新 attempt にfallbackする。
- `record_chapter_candidate()` に `draft_run_id` を追加し、`record_chapter_attempt()` へ伝播する。
- `_workspace_dirs()` を追加し、coordinator の公開APIが `Path` と `WorkspacePaths` の両方を受ける。`web.service` は `read.paths` を渡す。
- `run_chapter_draft()` は `project_lock` 内で `StateStore.load()` と context 構築を行う。
- `export_accepted_manuscript()` は `strip_chapter_scaffolding()` を通した本文だけを連結する。章の来歴は manifest が持つ。
- `build_book_cockpit(..., can_operate=)` を追加し、`startable` と review 操作の表示を authoring mode に限定する。

## 検証結果

- focused: coordinator / cockpit / exporter / drafting / web cockpit API — PASS。
- `NO_COLOR=1 uv run pytest` — 1121 passed / 2 skipped。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。

## 関連ファイル

- `src/living_narrative/book/coordinator.py`
- `src/living_narrative/book/cockpit.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/exporter.py`
- `src/living_narrative/web/service.py`
- `src/living_narrative/web/page.py`
- `tests/book/test_chapter_production_coordinator.py`
- `tests/book/test_cockpit.py`
- `tests/book/test_exporter.py`
- `tests/web/test_book_cockpit_api.py`
