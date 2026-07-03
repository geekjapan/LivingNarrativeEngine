## 1. User Mode モデル

- [ ] 1.1 `UserMode` enum(`watcher` `assistant_gm` `full_gm` `author` `player_character` `god`)を Pydantic v2 モデルとして定義する。
- [ ] 1.2 モードごとの権限マトリクス(許可介入タイプ集合・diff レビュー要否・gm_vault 表示可否)をデータとして定義する。
- [ ] 1.3 `player_character` モードの `char_id` バインディングを project セッション設定に追加する。
- [ ] 1.4 権限マトリクスに基づく介入タイプの許可判定関数を実装し、intervention capability の Interpreter 生成時チェックへデータとして供給する(未許可介入は Interpreter が生成時に拒否 + エラー理由返却。本 capability 内で生成済み intervention を二重に却下する経路は作らない。design.md D7)。

## 2. Autonomy Level モデル

- [ ] 2.1 `AutonomyLevel` enum(`manual` `assist` `auto` `watch` `god`)を定義する。
- [ ] 2.2 レベルごとのターン停止セマンティクス(毎ターン停止/条件停止/N停止/非停止)を実装する。

## 3. Mode × Level 正規化

- [ ] 3.1 矛盾する組み合わせの検出ルール(watcher+manual/god → watch、player_character+auto/watch/god → assist)を条件式リストとして実装する。
- [ ] 3.2 正規化発生時の警告ログ出力を実装する。
- [ ] 3.3 有効な組み合わせが正規化されないことを保証するユニットテストを書く。

## 4. 停止条件評価

- [ ] 4.1 10条件(character_death, major_canon_change, relationship_threshold_crossing, major_secret_reveal, checker_error, leak_suspicion, heavy_roll_failure, scene_end, target_turn_count_reached, stop_condition)の判定関数を実装する(spec-foundation D119)。`character_death`・`heavy_roll_failure`・`scene_end` は spec-foundation D123 の具体的フィールド(state diff 中の CharacterState.status の dead 遷移、rolls.yaml 中の roll の severity: critical かつ失敗 outcome、state diff 中の SceneState.status の ended 遷移)を機械的に評価し、自然文解釈や推測に頼らない。
- [ ] 4.2 プロジェクト設定(enable/disable、閾値)の読み込みとデフォルト値フォールバックを実装する。`stop_condition` は enable/disable の対象外とする(常に有効)。
- [ ] 4.3 レベル別適用ルール(assist/auto は全10条件、watch/god は checker_error・scene_end・target_turn_count_reached・stop_condition の4条件のみ)を実装する。
- [ ] 4.4 停止条件評価の呼び出しをターンパイプラインの Check→Commit 境界(design.md D2)に統合する。`stop_condition` は当該ターンで確定した `stop_condition` 介入の有無を判定材料とする。

## 5. GM レビューゲート

- [ ] 5.1 pending state diff の保持・提示データ構造を実装する。
- [ ] 5.2 accept_all / reject_all / partial / edit / rerun_turn の各決定処理を実装する。`partial`/`edit` はターンパイプラインのフェーズ実行を経由せず、state-model の diff 適用 API と add-turn-pipeline が公開する事後操作向けユーティリティを直接呼び出す(design.md D8、turn-pipeline grill Q4 裁定)。`rerun_turn` は旧 attempt の退避(`turn_NNNN_discarded_<n>` へのリネーム)と `review.yaml` への決定記録のみをこの事後操作として直接呼び出しで完結させ、新しい attempt は通常のターン実行として TurnPipeline の8フェーズ全体(Load〜Commit)を経由して実行する(design.md D8)。
- [ ] 5.3 edit 決定時、state diff スキーマ(spec-foundation §5.1)での再検証を実装する(検証失敗時は pending review を維持し再編集可能にする)。
- [ ] 5.4 決定内容を `review.yaml` に記録する処理を実装する(spec.md 記載のフィールド: turn/decision/decided_at/decided_by/applied_change_indices/edit_diff/resulting_turn_status/auto_applied)。`decision: reject_all` は export-replay capability が正史除外判定に参照するマーカーである(spec-foundation D120)。
- [ ] 5.5 決定→ターンステータス写像(accept_all/partial/edit成功→applied、reject_all→変更ゼロ件のapplied)を実装する。

## 6. Rerun セマンティクス

- [ ] 6.1 既定(新規シーケンス消費)での rerun 実行を実装する。
- [ ] 6.2 `--replay-same-seed` 指定時の乱数消費数巻き戻しを実装する。
- [ ] 6.3 破棄された旧ターン artifact を `turn_NNNN_discarded_<attempt連番>` へリネームして保持する処理を実装する(spec-foundation §6 D112、design.md D6。add-turn-pipeline が公開するユーティリティを利用し、命名契約を独自に分岐させない)。
- [ ] 6.4 破棄対象ターンに属する `interventions.yaml` エントリへ `superseded_by_rerun: true` を付与する処理を実装する(design.md D6、add-intervention との調整事項の確定分)。

## 7. Resume

- [ ] 7.1 ワークスペースから最終適用ターン番号を検出する処理を実装する(`turn_NNNN` のみ対象、`turn_NNNN_discarded_*` は除外)。
- [ ] 7.2 pending review の有無を検出する処理を実装する。
- [ ] 7.3 現存する `turn_NNNN/meta.yaml` と全ての `turn_NNNN_discarded_*/meta.yaml` の rng 消費数を合算し、乱数エンジンの状態を再構築する処理を実装する(design.md D6)。
- [ ] 7.4 pending-review-first ルール(他操作より resume 時の pending review 提示を優先)を実装する。
- [ ] 7.5 project 内一意 id カウンタ(`event_NNNN`・`diff_NNNN`・`roll_NNNN`・`int_NNNN`)の次番号を、現存する全 `turn_NNNN` と全 `turn_NNNN_discarded_*` の該当 artifact(`events.yaml`・`state_diff.yaml`/`state_diff_pre_review.yaml`・`rolls.yaml`・`intervention.yaml`)およびプロジェクト全体の `interventions.yaml` の走査から復元する処理を実装する(draw 数や他カウンタからの導出は行わない)。

## 8. Auto N ターンループ

- [ ] 8.1 N ターンまたは停止条件到達までの連続実行ループを実装する。
- [ ] 8.2 ループ中の各ターンが通常のターン実行と同一の artifact/レビュー契約に従うことを保証する。
- [ ] 8.3 中断安全性(Ctrl-C 等での中断時、Commit 済み状態の保持と partial artifact の保存)を実装する。

## 9. God Mode ログ強制

- [ ] 9.1 god モードの直接編集操作を state diff として生成する経路を実装する(diff 生成を経由しない直接書き換えパスを作らない)。
- [ ] 9.2 レビューバイパス時も `review.yaml` に自動適用であることを記録する処理を実装する。

## 10. テスト

- [ ] 10.1 モード×介入タイプ許可判定のテーブル駆動テストを書く(全モード×代表的介入タイプの組み合わせ)。
- [ ] 10.2 mode×level 正規化マトリクスのテーブル駆動テストを書く(全組み合わせ)。
- [ ] 10.3 停止条件×レベル適用マトリクスのテーブル駆動テストを書く。
- [ ] 10.4 pending review が存在する状態からの resume テストを書く(pending-review-first を検証)。
- [ ] 10.5 auto ループが checker_error 等の停止条件で正しく停止することを検証するテストを書く(mock provider 使用)。
- [ ] 10.6 rerun の既定(新規シーケンス)と `--replay-same-seed`(同一シーケンス)双方の乱数結果を検証するテストを書く。
- [ ] 10.7 god モードの編集が常に diff として記録されることを検証するテストを書く。
- [ ] 10.8 rerun で破棄された `turn_NNNN_discarded_*` の rng 消費数が resume の累積計算に含まれることを検証するテストを書く(design.md D6)。
- [ ] 10.9 `character_death`(state diff の CharacterState.status: dead 遷移)・`heavy_roll_failure`(rolls.yaml の severity: critical かつ失敗 outcome。critical な成功 roll では停止しないことを含む)・`scene_end`(state diff の SceneState.status: ended 遷移)の具体的フィールド評価を検証するテストを書く(spec-foundation D123)。
- [ ] 10.10 resume 後に生成される event / diff / roll / intervention の id が、破棄済み attempt を含む既存の最大 id の次番号から採番され、id の再利用が発生しないことを検証するテストを書く。

## 11. ドキュメント

- [ ] 11.1 `docs/` にモード権限マトリクスと停止条件マトリクスの一覧表を追記する。
- [ ] 11.2 resume / rerun / auto ループの CLI 利用例(cli capability 実装後に確定)への参照を残す TODO を記載する。
