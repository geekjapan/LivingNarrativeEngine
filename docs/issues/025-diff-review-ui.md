---
id: 025
title: Web UI — State Diff Review(Track Bの最終ノード)
status: done
created: 2026-07-07
---

# 025: State Diff Review UI(Track B、020/021-022/023/024の続き)

## 背景

DAG Track B(`docs/plan/feature-dag.md` Track B行、025番、depends on 020・022)の最終ノード。ターンが `pending_review`/`stopped_for_review` で止まったとき、GMは提案された state diff を検討して解決する必要があるが、web層は `accept_all`/`reject_all` しか公開しておらず(021-022の実装メモに記載済み)、`partial`(選択した変更だけ適用)は CLI (`living-narrative review --decision partial --apply`) からしかできなかった。ロール/チェックログの閲覧自体は024の `GET .../gm/turn/{n}` で既にカバー済みなので、本Issueのスコープは「diffの中身を見て、選択的に承認/棄却するUI」に絞る。

## 設計

**決定サーフェス**: `session/review.py` の `resolve_review` は `accept_all`/`reject_all`/`partial`/`edit`/`rerun_turn` の全てをサポートしており、`partial` は `selected_change_indices: set[int]` を受けて `state/diff.py::apply_state_diff` の `selected_change_indexes` にそのまま渡す(CLIの `cli/review.py --decision partial --apply` と同じ経路)。web層はこの既存プリミティブを呼ぶだけで `partial` を追加露出できる ── 新しい解決ロジックは書かない。`edit`(diffの手動編集)と `rerun_turn`(RNGを揃えた再実行)はUIがまだ無いため引き続きCLI専用。

**API**(`web/service.py` / `app.py`、読み取り専用の GET は FastAPI-free な service層、書き込みは既存 `resolve_review` 経由):

1. `GET /api/project/{name}/review` — 直近のpending/stopped-for-reviewターンの提案diffを返す:
   `{pending, turn, status, changes: [{index, target, id, path, op, value, visibility, source_event}], rejected_changes: [...], checks: [...findings]}`。pending turnが無ければ `{pending: false, turn: null, status: null, changes: [], rejected_changes: [], checks: []}`。`changes` の `index` は元の `state_diff.yaml` の変更順そのもの ── `partial` の `selected_indexes` はこのインデックスを参照する。
2. `POST /api/project/{name}/review` body拡張: `{"decision": "accept_all"|"reject_all"|"partial", "selected_indexes": [int]}` ── `partial` は `selected_indexes` が空だと422。`edit`/`rerun_turn` は引き続き400(CLI専用)。

**UI**(`web/page.py`): pending時に表示される「レビュー待ち」パネル ── 変更ごとにチェックボックス付きの行(target/path/op/value/visibilityバッジ)を並べたテーブル、safety-checker findingsの一覧、`accept_all`/`reject_all`/`選択のみ適用`(partial)ボタン。

**制約**: `src/living_narrative/web/**`・`tests/web/**` のみ、コア(`session/review.py`・`state/diff.py`等)は不変更。

## 完了条件

- [x] `GET .../review` がpending/not-pendingどちらの形も返す
- [x] `POST .../review` で `accept_all`/`reject_all`/`partial` が解決でき、`partial` は選択した変更だけを状態に適用する(未選択分は状態に反映されない)
- [x] `partial` で `selected_indexes` が空だと422
- [x] `edit`/`rerun_turn` は引き続き400(CLI専用のまま)
- [x] 404/409は既存エンドポイント群と一貫(プロジェクト不明→404、pending turn無し→409)
- [x] UIにレビューパネル(diffテーブル+チェックボックス+3ボタン+checks findings表示)がある
- [x] 既存613テスト回帰なし、ruffクリーン

## 関連ファイル

- 変更: `src/living_narrative/web/{app,service,page}.py`
- 新規テスト: `tests/web/test_review_ui_api.py`
- 既存テスト更新: `tests/web/test_turn_controls.py`(`partial`が解禁されたため、未対応デコレーション確認用の入力を `edit` に差し替え)
- 参照のみ: `session/review.py`(`resolve_review`/`ReviewDecision`)、`state/diff.py`(`apply_state_diff`の`selected_change_indexes`)、`cli/review.py`(`partial`のCLI経路)、`safety/registry.py`(`Finding`/`checks.yaml`の形)
- DAG: `docs/plan/feature-dag.md`(Track B、025がTrack Bの最終ノード)
