---
id: 093
title: Reader-safe章コンテキスト、決定的compiler、chapter reviewを導入する
status: completed
created: 2026-08-17
type: implementation
priority: P0
parent: 092
blocked_by: [091, 092]
labels: [long-form, chapters, quality]
---

# 093: Reader-safe章コンテキスト、決定的compiler、chapter reviewを導入する

## 実装結果

- `build_chapter_context()`はBookPlan、reader state、sceneのreader-visible facts、最新memory summaryのみを投影する。GM-only state、character secret、private mindはcontextへ入らない。
- `compile_chapter()`はreader-visible narration segmentをMarkdownへ決定的に連結し、chapter ID、act ID、source turnのprovenanceをfrontmatterに記録する。
- `review_chapter()`は外部tokenizerやLLMに依存しないCJK/Latin unit数でword-range hard gateを実行し、`accept`または`revise`を返す。

## 検証結果

- `NO_COLOR=1 uv run pytest tests/book` — 7 passed。
- `uv run ruff check src/living_narrative/book tests/book`、`uv run ruff format --check src/living_narrative/book tests/book`、`git diff --check` — PASS。

## 次の統合点

book coordinatorはchapter candidateとreviewをartifactとして保存し、accepted/revise decisionを`BookLedgerState`のtransaction-backed lifecycle変更へ変換する。
