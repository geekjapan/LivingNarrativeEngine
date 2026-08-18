---
id: 104
title: Cockpit ID/word投影、draft lock、continuity回収の不具合を直す
status: completed
completed: 2026-08-18
created: 2026-08-18
type: bugfix
priority: P0
parent: 101
blocked_by: []
labels: [long-form, web, continuity, transaction]
---

# 104: Cockpit ID/word投影、draft lock、continuity回収の不具合を直す

## 背景

Issue 096〜101 の長編制作経路に、Cockpit操作が動かない、目標文字数が投影されない、draftがworkspace lockを共有しない、accepted章がopen threadを閉じない、という4件の契約違反がある。

## 完了条件

- Cockpit UIはAPIの `chapter_id` を `data-chapter-id` に束縛し、start/accept/reviseがmutation endpointを呼ぶ。
- `CockpitChapter` はBookPlanの `target_word_range` を `target_min_words` / `target_max_words` として投影する。
- `run_chapter_draft` はcoordinator/turnと同じworkspace rootの `project_lock` を取る。
- `advance_continuity_ledger` は後続accepted章が被覆したthreadを `open_thread_ids` から外す。
- focused回帰、全test、ruff、format、diff checkを通す。

## 実装結果

- Cockpit UIは `chapter.chapter_id` をボタンと見出しに束縛する。
- `CockpitChapter` はBookPlanの word range を `target_min_words` / `target_max_words` として投影する。
- `run_chapter_draft` は `workspace_root/.lock` を取り、coordinator/turnと同一lock境界にする。
- `advance_continuity_ledger` は被覆済みthreadを `open_thread_ids` から除去する。

## 検証結果

- focused: cockpit / continuity / drafting / web cockpit API / page contract — PASS。
- `NO_COLOR=1 uv run pytest` — 1109 passed / 2 skipped。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。
- GitNexus `analyze --index-only` は成功。GitNexus MCPはtool discovery失敗のためimpact queryは未取得。

## 関連ファイル

- `src/living_narrative/web/page.py`
- `src/living_narrative/book/cockpit.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/continuity.py`
- `tests/web/test_web_app.py`
- `tests/web/test_book_cockpit_api.py`
- `tests/book/test_cockpit.py`
- `tests/book/test_drafting.py`
- `tests/book/test_continuity.py`
