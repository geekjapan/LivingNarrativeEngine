---
id: 021-022
title: Story Pane + Turn Controls(auto進行・停止・reviewのUI/API化)
status: done
created: 2026-07-07
---

# 021+022: Story Pane + Turn Controls(Track B、020の続き)

## 背景

DAG(docs/plan/feature-dag.md)Track B。020で作った FastAPI 骨格(`web/`)の上に、CLIの `turn`/`auto`/`review` 相当をAPI化し、ページ側にストーリーペイン+操作列を追加する。021(Story Pane)と022(Turn Controls)は実装上ファイル・エンドポイントが密結合するため1 issueにまとめる。

Track A(engine core: `pipeline/`/`agents/`/`state/`/`session/`/`narration/`)とはファイル素性が交差しないため worktree 並列で進行。本 issue のスコープは `src/living_narrative/web/**`・`tests/web/**`・`tests/cli/**`(必要なら `cli/serve.py`)のみで、コア側は既存関数を呼ぶだけで一切変更しない。

## 設計

1. **`POST /api/project/{name}/auto`** `{"turns": N}` — バックグラウンドスレッドで最大N ターンを連続実行。プロセス内レジストリ(`web/service.py` の `_RUN_STATES: dict[Path, _ProjectRunState]`、project dir 実パスをキーに)で実行状態を保持。二重起動は 409。
2. **`GET /api/project/{name}/run_status`** → `{running, current_turn, last_status, stopped_reason}`。ターンが `stopped_for_review`/`failed` で終わると自動的にそこで停止し `stopped_reason` に理由を記録。
3. **`POST /api/project/{name}/stop`** — 実行中フラグ(`threading.Event`)を立てるだけ。ループはターン境界(次のターン開始前)でチェックして穏やかに停止する。
4. **`POST /api/project/{name}/review`** `{"decision": "accept_all"|"reject_all"}` — 既存 `session/review.py::resolve_review` をそのまま呼ぶ(再実装しない)。pending reviewが無ければ409。
5. **`GET /api/project/{name}/turns?from=N`** — 構造化ターン一覧 `[{turn, status, text}]`(既存 `?from=N` 文字列連結エンドポイントとは別に新設。理由: 既存 `/narration` はプレーンテキストの単一連結を返す契約で固まっており、同じパスでレスポンス型を条件分岐させるより新エンドポイントの方が呼び出し側にとって型が安定する)。
6. **`page.py`**: ターンごとのブロック+ステータスバッジを表示するストーリーペイン、操作列(次のターン/auto N入力/stop/review accept_all/review reject_all)、実行中は `run_status` をポーリング、プロジェクト選択に現在ターン数を表示。

## 完了条件

- [x] auto happy path(小N、mock provider、run_status完了をポーリング)
- [x] auto二重起動で409
- [x] stop がターン境界で機能する(大きいNで開始→stop→途中で止まる)
- [x] review flow(stopped_for_review なターンを用意 → accept_all → 次ターンが進む)
- [x] 構造化ターン一覧が各ターンのstatusを含む
- [x] 既存テスト(web/cli/コア)に回帰なし

## 関連ファイル

- 変更: `src/living_narrative/web/app.py`, `src/living_narrative/web/service.py`, `src/living_narrative/web/page.py`
- 新規テスト: `tests/web/test_turn_controls.py`
- 参照のみ: `session/review.py::resolve_review`, `session/resume.py::restore_resume_state`, `pipeline/turn_numbering.py::read_turn_status`, `pipeline/driver.py::TurnPipeline`
- DAG: `docs/plan/feature-dag.md`

## 実装時の逸脱(deviation)

- 020の設計文中の想定と異なり、構造化ターン一覧は `/narration?structured=1` ではなく別パス `/turns` にした(上記4参照)。
- auto実行のバックグラウンド方式は FastAPI `BackgroundTasks` ではなく素の `threading.Thread` を採用: `run_status` ポーリング・`stop` は BackgroundTasks のリクエストスコープ外からも参照できる必要があり、`web/service.py` は元々 FastAPI 非依存(020の設計方針)なので、スレッドベースの方がテスト容易性(pytest から素の関数呼び出しで検証可能)と既存方針の両方に合致する。
