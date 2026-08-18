---
id: 106
title: 長編制作mutationをauthoring modeに限定しCIの性能予算を安定させる
status: completed
completed: 2026-08-18
created: 2026-08-18
type: bugfix
priority: P1
parent: 101
blocked_by: []
labels: [long-form, web, security, ci]
---

# 106: 長編制作mutationをauthoring modeに限定しCIの性能予算を安定させる

## 背景

`docs/design/long-form-cockpit-architecture.md` §2 は長編制作操作を `author` / `full_gm` / `god` に限定している。しかし Cockpit の start / accept / revise は `player_character` だけを拒否しており、interventionを1つも持たない `watcher` や `assistant_gm` から章のlifecycleを変更できる。

あわせて、CI の 50 turn smoke がローカル実測 21.9 秒に対し共有ランナーで 68.9 秒かかり、60 秒予算を超えて `test-py312-web` が失敗した。同一コミットの別 run では通過しており、性能回帰ではなくランナー変動である。

## 完了条件

- `POST /book/chapters/{id}/start|accept|revise` は authoring mode 以外を 403 にする。
- 権限判定は `session.mode` の permission matrix を正本とし、web 側に第二の定義を作らない。
- 非 authoring mode でも Cockpit の読取り (`GET /book/cockpit`) は維持する。
- CI テストジョブは共有ランナーの変動を吸収する性能予算で実行する。
- focused回帰、全test、ruff、format、diff checkを通す。

## 実装結果

- `session.mode.BOOK_AUTHORING_MODES` と `is_book_authoring_allowed()` を追加した。
- `web.app` に `_require_book_authoring_access()` を追加し、book mutation 3経路へ適用した。
- 読取りは従来どおり `_require_sensitive_session_access()` のままとした。
- CI テストジョブに `LNE_PERF_BUDGET_SCALE: "2"` を設定した（既存の予算スケール機構を再利用）。

## 検証結果

- focused: `tests/web` — 124 passed / 2 skipped。
- `NO_COLOR=1 uv run pytest` — 全件 PASS。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。

## 関連ファイル

- `src/living_narrative/session/mode.py`
- `src/living_narrative/web/app.py`
- `tests/web/test_book_cockpit_api.py`
- `.github/workflows/ci.yml`
