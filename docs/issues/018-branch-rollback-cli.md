---
id: 018
title: branch/rollback CLI(保存済みinverse diffを使う巻き戻しと分岐)
status: done
created: 2026-07-07
---

# 018: branch / rollback CLI

## 背景

DAG Track A(並列可ノード)。Phase 5機能・D109(branching data format)/D112(discarded保存)/D120整合。inverse diff は毎ターン `runs/turn_NNNN/inverse_diff.yaml` に保存済み(`state/diff.py rollback()` 実装済み・`load_inverse_diff` あり)だが、それを使うユーザー向けコマンドが無い。

## 設計

1. **`living-narrative rollback --project P --to-turn N`**: 現在ターンから N+1..current の inverse diff を逆順適用(既存 `rollback()`)して state を N 時点へ戻す。巻き戻したターンの `runs/turn_XXXX` は削除せず `turn_XXXX_rolledback_<ts>` にリネーム保存(D112の精神: 破壊しない)。timeline も inverse に含まれるため自動で切り詰まる。実行前に確認プロンプト(`--yes` でスキップ)
2. **`living-narrave branch --project P --from-turn N --output DIR`**: プロジェクト全体をDIRへ複製し、複製側で N 時点まで rollback。元プロジェクトは無傷。`project.yaml` の title に ` (branch@N)` を付記
3. ガード: N >= current は no-op エラー、inverse_diff.yaml 欠損ターンがあれば中断(部分巻き戻しはしない)、pending_review 状態では rollback 拒否(先にreview解決)
4. RNG状態: 巻き戻し後の再実行は同seedでも介入等で分岐しうる — rolls はターンartifactに残るため再現性検証は可能。rng_state の巻き戻しは既存の resume 機構(meta/rolls からの復元)に従う(要確認 — pipeline/rng_state.py)

## 完了条件

- [x] rollback: Nターン戻して state/timeline が一致(mockで turn5→3、感情・threads・pressure・timeline全部戻る)、rolledback dirs保存
- [x] rollback後に再度 turn 実行で turn N+1 から番号が振り直される(既存 turn_numbering と整合)
- [x] branch: 複製先が N 時点 state で独立に進行、元は無傷
- [x] ガード3種(future N / missing inverse / pending_review)
- [x] mock全テストpass(579+)(604 passing; real-LLMスモーク不要 — 決定論的なstate machineryなのでmockカバレッジで十分)

## 実装メモ(2026-07-07)

- **前提の食い違い**: 設計は「inverse diff は毎ターン保存済み」としていたが、実際は `session/review.py`(レビュー承認)と `session/god.py`(godモード編集)だけが `save_apply_artifacts` を呼んでおり、通常の `commit_mode="auto"` パス(`pipeline/driver.py` `TurnPipeline.run` の commit フェーズ)では `inverse_diff.yaml` が一切保存されていなかった。rollback の前提が成立しないため、`driver.py` の auto-apply 分岐にも `save_apply_artifacts` 呼び出しを追加した(既存テストに影響なし、604件green)。
- **rolledback dir命名**: `turn_NNNN_rolledback_<n>`(discardと同じ連番方式、タイムスタンプなし)。`_discarded_` と異なる接尾辞にすることで `pipeline/rng_state.py`/`session/resume.py` が使う `ANY_TURN_DIR_RE` に一致させず、巻き戻したターンのRNG draws・rolls・(resumeの)last-applied-turn判定から自然に除外されるようにした(event/intervention IDは別ロジックでディレクトリ名に関係なく全件走査するため、巻き戻し後も重複しない)。
- **新規ファイル**: `src/living_narrative/session/rollback.py`(`plan_rollback`/`execute_rollback`/`copy_project_for_branch`/`append_branch_title_suffix`)、`src/living_narrative/cli/rollback.py`、`src/living_narrative/cli/branch.py`。
- **既存ファイル変更**: `pipeline/turn_numbering.py`(`_existing_turn_numbers`→公開`existing_turn_numbers`、`rollback_turn_directory`追加)、`pipeline/__init__.py`(export追加)、`pipeline/driver.py`(上記)、`cli/__init__.py`(コマンド登録)。
- **テスト**: `tests/cli/test_rollback_branch.py`(8ケース: 状態復元、番号振り直し、ガード3種、確認プロンプト、branch独立進行、branch出力先の重複エラー)。

## 関連ファイル

- `src/living_narrative/state/diff.py`(rollback/load_inverse_diff既存)
- `src/living_narrative/cli/`(rollback/branchサブコマンド新設)
- `src/living_narrative/pipeline/turn_numbering.py` / `pipeline/rng_state.py`(番号・RNG整合)
- `src/living_narrative/workspace/`(複製)
- DAG: `docs/plan/feature-dag.md`
