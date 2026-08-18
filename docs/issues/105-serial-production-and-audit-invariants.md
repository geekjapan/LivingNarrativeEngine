---
id: 105
title: 直列制作・workspace path・budget再開・export/benchmark不変条件を直す
status: completed
completed: 2026-08-18
created: 2026-08-18
type: bugfix
priority: P1
parent: 103
blocked_by: []
labels: [long-form, coordinator, drafting, review, export, benchmark]
---

# 105: 直列制作・workspace path・budget再開・export/benchmark不変条件を直す

## 背景

PR 30 の未解決レビューは、長編制作の監査可能性を壊す契約違反を指摘している。一部（Cockpit word投影、open thread回収）は Issue 104 で直済み。残件は、同時running、カスタムworkspace path、budget到達時の同一attempt再開、journal世代、compile scaffoldingの字数、export世代、benchmark fingerprintである。

## 完了条件

- 他章が制作中なら `start_chapter_production` を拒否し、Cockpitは開始ボタンを出さない。
- `run_chapter_draft` は `load_project()` が解決した workspace path だけを使う。
- book attempt上限ちょうどでも、同一attemptの保存済みresponse/部分runは再開できる。
- chapter lifecycle journalは現行BookPlan世代で名前空間化され、置換提案後に旧journalを再開しない。
- 品質ゲートの body units は compile frontmatter / heading / planned-goal を除外する。
- manuscriptとmanifestは世代markerを最後に書き、混在世代を検出できる。
- benchmark fingerprintは章順・attempt identity・accepted attemptを束縛する。
- focused回帰、全test、ruff、format、diff checkを通す。

## 関連ファイル

- `src/living_narrative/book/coordinator.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/budget.py`
- `src/living_narrative/book/cockpit.py`
- `src/living_narrative/book/review.py`
- `src/living_narrative/book/chapters.py`
- `src/living_narrative/book/exporter.py`
- `src/living_narrative/book/benchmark.py`
- `src/living_narrative/web/page.py`
- `tests/book/`
- `tests/web/test_book_cockpit_api.py`

## 実装結果

- 他章が RUNNING/CANDIDATE/REVIEW/REVISING なら start を拒否し、Cockpitは `startable` だけを表示する。
- schedulerは制作中章があるとき次章startより `wait_for_review` を返す。
- chapter journalはBookPlan hashで名前空間化し、置換提案後に旧running journalを再開しない。
- draftは `load_project()` の解決pathを使い、同一attemptはbook上限でもresponseから再開する。
- reviewの body units は compile scaffolding を除外する。
- exportは manuscript/manifest をstagingし、`manuscript_generation.yaml` を最後に書く。
- benchmark fingerprintは章順・attempt identity・accepted attemptを束縛する。

## 検証結果

- focused book/web回帰 — PASS。
- `NO_COLOR=1 uv run pytest` — 1116 passed / 2 skipped。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。
