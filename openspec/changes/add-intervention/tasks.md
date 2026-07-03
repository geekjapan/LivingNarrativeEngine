## 1. スキーマと権限テーブル

- [ ] 1.1 Intervention の Pydantic v2 モデル(id/turn/user_role/type/target/content/constraints/visibility)を実装する
- [ ] 1.2 `type` enum(15種)を定義する
- [ ] 1.3 `target` の enum(state-model target enum + `roll`)と id 参照フィールドを実装する
- [ ] 1.4 `int_NNNN` の project 内一意 id 採番機構を実装する(spec-foundation §3 準拠)
- [ ] 1.5 type→handling-status(専用ルーティングあり/なし)のマッピングを実装する(9種 vs 6種)
- [ ] 1.6 permission table(`type -> set[user_mode]`)をデータとして定義し、15種全ての行を埋める
- [ ] 1.7 `check_permission(type, user_mode) -> Ok | Rejection` を実装する
- [ ] 1.8 スキーマ検証・型別ハンドリング状況・permission table の単体テストを書く

## 2. 構造化直接入力パス

- [ ] 2.1 型付きフィールドを直接指定して Intervention を構築する API を実装する
- [ ] 2.2 直接入力パスにも permission hook を適用する
- [ ] 2.3 直接入力パスの正常系・permission rejection のテストを書く

## 3. Intervention Interpreter

- [ ] 3.1 Interpreter の response_schema(`interventions: list[Intervention]` + `confidence` + `interpretation_summary`)を定義する
- [ ] 3.2 llm-provider の `complete(messages, response_schema)` を呼び出す Interpreter 実装を書く
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
- [ ] 4.8 未ハンドル6種を関係する agent のコンテキストへ constraints として提示する共通配線を実装する
- [ ] 4.9 ルーティングごとのスコープ遵守テスト(character_directive の他キャラクター非漏洩等)を書く

## 5. reveal_control 意味論

- [ ] 5.1 `must-not-reveal` / `reveal-now` マークの中間データ表現を実装する
- [ ] 5.2 Commit フェーズでの Reader State 昇格ブロック/即時昇格ロジックを実装する
- [ ] 5.3 両ケースのテスト(ブロックされるケース・即時昇格されるケース)を書く

## 6. Intervention 履歴インデックス

- [ ] 6.1 `interventions.yaml`(プロジェクト全体累積)のスキーマを定義する
- [ ] 6.2 ターンごとの追記(既存エントリを上書きしない)を実装する
- [ ] 6.3 event id / state diff id への source reference 記録を実装する
- [ ] 6.4 複数ターンにまたがる累積・追跡可能性のテストを書く

## 7. 統合テストとドキュメント

- [ ] 7.1 9種の専用ハンドリングタイプそれぞれについて end-to-end(Interpreter or 直接入力 → intervention.yaml → ルーティング先反映)テストを書く
- [ ] 7.2 permission rejection の end-to-end テスト(禁止 user_mode での canon_edit 等)を書く
- [ ] 7.3 `docs/` に intervention capability の使い方(自由文介入の例、直接入力 API、permission table)を追記する
