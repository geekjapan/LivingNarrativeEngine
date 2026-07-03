## 1. User Mode モデル

- [ ] 1.1 `UserMode` enum(`watcher` `assistant_gm` `full_gm` `author` `player_character` `god`)を Pydantic v2 モデルとして定義する。
- [ ] 1.2 モードごとの権限マトリクス(許可介入タイプ集合・diff レビュー要否・gm_vault 表示可否)をデータとして定義する。
- [ ] 1.3 `player_character` モードの `char_id` バインディングを project セッション設定に追加する。
- [ ] 1.4 権限マトリクスに基づく介入タイプの許可判定関数を実装する(未許可介入は拒否 + エラー理由返却)。

## 2. Autonomy Level モデル

- [ ] 2.1 `AutonomyLevel` enum(`manual` `assist` `auto` `watch` `god`)を定義する。
- [ ] 2.2 レベルごとのターン停止セマンティクス(毎ターン停止/条件停止/N停止/非停止)を実装する。

## 3. Mode × Level 正規化

- [ ] 3.1 矛盾する組み合わせの検出ルール(watcher+manual/god → watch、player_character+auto/watch/god → assist)を条件式リストとして実装する。
- [ ] 3.2 正規化発生時の警告ログ出力を実装する。
- [ ] 3.3 有効な組み合わせが正規化されないことを保証するユニットテストを書く。

## 4. 停止条件評価

- [ ] 4.1 9条件(character_death, major_canon_change, relationship_threshold_crossing, major_secret_reveal, checker_error, leak_suspicion, heavy_roll_failure, scene_end, target_turn_count_reached)の判定関数を実装する。
- [ ] 4.2 プロジェクト設定(enable/disable、閾値)の読み込みとデフォルト値フォールバックを実装する。
- [ ] 4.3 レベル別適用ルール(assist/auto は全条件、watch/god は checker_error・scene_end・target_turn_count_reached のみ)を実装する。
- [ ] 4.4 停止条件評価の呼び出しをターンパイプラインの Check→Commit 境界(design.md D2)に統合する。

## 5. GM レビューゲート

- [ ] 5.1 pending state diff の保持・提示データ構造を実装する。
- [ ] 5.2 accept_all / reject_all / partial / edit / rerun_turn の各決定処理を実装する。
- [ ] 5.3 edit 決定時、state diff スキーマ(spec-foundation §5.1)での再検証を実装する。
- [ ] 5.4 決定内容を `review.yaml` に記録する処理を実装する。

## 6. Rerun セマンティクス

- [ ] 6.1 既定(新規シーケンス消費)での rerun 実行を実装する。
- [ ] 6.2 `--replay-same-seed` 指定時の乱数消費数巻き戻しを実装する。
- [ ] 6.3 破棄された旧ターン artifact の非削除・監査可能な保持を実装する。

## 7. Resume

- [ ] 7.1 ワークスペースから最終適用ターン番号を検出する処理を実装する。
- [ ] 7.2 pending review の有無を検出する処理を実装する。
- [ ] 7.3 `meta.yaml` の rng 消費数を累積し、乱数エンジンの状態を再構築する処理を実装する。
- [ ] 7.4 pending-review-first ルール(他操作より resume 時の pending review 提示を優先)を実装する。

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

## 11. ドキュメント

- [ ] 11.1 `docs/` にモード権限マトリクスと停止条件マトリクスの一覧表を追記する。
- [ ] 11.2 resume / rerun / auto ループの CLI 利用例(cli capability 実装後に確定)への参照を残す TODO を記載する。
