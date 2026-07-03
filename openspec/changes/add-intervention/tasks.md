## 1. スキーマと権限テーブル

- [ ] 1.1 Intervention の Pydantic v2 モデル(id/turn/user_role/type/target/content/constraints/visibility)を実装する
- [ ] 1.2 `type` enum(15種)を定義する
- [ ] 1.3 `target` の enum(state-model target enum + `roll`)と id 参照フィールドを実装する
- [ ] 1.4 `int_NNNN` の project 内一意 id 採番機構を実装する(spec-foundation §3 準拠)
- [ ] 1.5 type→handling-status(本change内専用ルーティングあり/session-autonomy委譲(stop_condition)/専用ハンドラなし)の3値マッピングを実装する(9種 / 1種 / 5種)
- [ ] 1.6 普遍的不変条件(canon_edit/hidden_truth_edit → full_gm/god)をハードコードし、それ以外は外部注入される permission table を受け取るプラガブルな判定機構を実装する。permission table 未注入時の既定値は不変条件を除き全許可(permissive)とする
- [ ] 1.7 `check_permission(type, user_mode, permission_table) -> Ok | Rejection` を実装する(`permission_table` は既定で permissive、外部注入で上書き可能)
- [ ] 1.8 スキーマ検証・型別ハンドリング状況・permission table の単体テストを書く

## 2. 構造化直接入力パス

- [ ] 2.1 型付きフィールドを直接指定して Intervention を構築する API を実装する
- [ ] 2.2 直接入力パスにも permission hook を適用する
- [ ] 2.3 直接入力パスの正常系・permission rejection のテストを書く

## 3. Intervention Interpreter

- [ ] 3.1 Interpreter の response_schema(`interventions: list[InterventionDraft]`(id/turn/user_role を含まない部分スキーマ) + `confidence` + `interpretation_summary`)を定義する
- [ ] 3.2 llm-provider の `complete(messages, response_schema)` を呼び出す Interpreter 実装を書く
- [ ] 3.2b Interpreter 出力の各 `InterventionDraft` に id/turn/user_role を補完し、正規の Intervention として検証する処理を実装する
- [ ] 3.3 未分類テキストを `scene_directive` にフォールバックさせるプロンプト/後処理を実装する
- [ ] 3.4 mock provider 用の fixture(自由文入力 → 期待 Intervention 群)を用意する
- [ ] 3.5 fixture ベースの決定的テスト(§7.2 の例を含む複数意図分解、未分類フォールバック)を書く
- [ ] 3.6 同一 seed・同一入力での再現性テストを書く

## 4. パイプライン統合とルーティング

- [ ] 4.1 `add-turn-pipeline` の Intervene フェーズ no-op 実装を、Interpreter/直接入力を呼び出す実装に置き換える
- [ ] 4.2 `intervention.yaml`(介入あり/なし双方)の書き込みを実装する
- [ ] 4.3 `character_directive` を対象キャラクターのコンテキストにのみ渡す配線を実装する
- [ ] 4.4 `world_directive` / `event_injection` を World Simulator へ渡す配線を実装する
- [ ] 4.5 `tone_control` / `reveal_control` を Narrator 制約へ渡す配線を実装する
- [ ] 4.6 `dice_roll_request` を Conflict Resolver 経由で Random Engine 判定要求へ渡す配線を実装する
- [ ] 4.7 `canon_edit` / `hidden_truth_edit` を State Manager 経由の state diff エントリへ変換する実装を書く(source_event 参照必須)
- [ ] 4.8 未ハンドル5種(`probability_bias`/`pacing_control`/`scene_pivot`/`relationship_edit`/`memory_edit`)を関係する agent のコンテキストへ constraints として提示する共通配線を実装する。`stop_condition` は `intervention.yaml` への保存のみ行い、この共通配線の対象外とする(session-autonomy が別途消費する)
- [ ] 4.9 ルーティングごとのスコープ遵守テスト(character_directive の他キャラクター非漏洩等)を書く

## 5. reveal_control 意味論

- [ ] 5.1 `must-not-reveal` / `reveal-now` マークの中間データ表現を実装する
- [ ] 5.2 BuildDiff スロット(agent-runtime の State Manager 実装)が参照する Reader State 昇格ブロック/即時昇格フィルタを実装する(turn-pipeline への新規 Commit hook 追加はしない)
- [ ] 5.3 両ケースのテスト(ブロックされるケース・即時昇格されるケース)を書く

## 6. Intervention 履歴インデックス

- [ ] 6.1 `interventions.yaml`(プロジェクト全体累積、`superseded_by_rerun` フィールドを含む)のスキーマを定義する
- [ ] 6.2 ターンごとの追記(既存エントリを上書きしない、Commit フェーズ完了時点で1回のみ書き込む)を実装する
- [ ] 6.3 event id / state diff id への source reference 記録(Commit フェーズ完了後に確定した値のみを用いる)を実装する
- [ ] 6.4 複数ターンにまたがる累積・追跡可能性のテストを書く
- [ ] 6.5 rerun 後に破棄された attempt のエントリを `superseded_by_rerun: true` へ更新し、新しい Commit 完了後に新規エントリを追記するテストを書く

## 7. 統合テストとドキュメント

- [ ] 7.1 9種の専用ハンドリングタイプそれぞれについて end-to-end(Interpreter or 直接入力 → intervention.yaml → ルーティング先反映)テストを書く
- [ ] 7.2 permission rejection の end-to-end テスト(禁止 user_mode での canon_edit 等)を書く
- [ ] 7.3 `docs/` に intervention capability の使い方(自由文介入の例、直接入力 API、permission table)を追記する
