## 1. Context Builder

- [ ] 1.1 `living_narrative.agents.context_builder` に `build_character_context` を実装する(WorldStateBundle 入力の純粋関数)
- [ ] 1.2 `build_world_context`(World Simulator / State Manager 用の全状態参照コンテキスト、出力タグ付け前提)を実装する
- [ ] 1.3 直近 N 件(既定値 20、`project.yaml` で上書き可能)イベント切り詰め + 関連 relationships 抽出ロジックを実装する
- [ ] 1.4 adversarial fixture(他者 private_mind・gm_vault・hidden_from イベントを含む WorldStateBundle)を用いた単体テストを作成し、spec の各 Scenario を再現する

## 2. Agent I/O スキーマ

- [ ] 2.1 `CharacterAgentInput` / `CharacterAgentOutput`(action_candidates[target_id 任意] / emotion_deltas / goal_updates)を Pydantic v2 で定義する
- [ ] 2.2 `WorldSimulatorOutput`(parameter_drifts / faction_moves / background_events[target_id 任意])を定義する
- [ ] 2.3 `ConflictResolverOutput`(resolved_events: state-model Event 準拠)を定義する
- [ ] 2.4 `StateManagerOutput`(state_diff: state-model StateDiff 準拠 / rejected_changes: 拒否理由付きリスト)を定義する
- [ ] 2.5 スキーマのラウンドトリップ(シリアライズ/デシリアライズ)テストを作成する

## 3. Character Agent

- [ ] 3.1 `living_narrative.agents.character` に Character Agent を実装し、llm-provider の `complete` を通じて構造化出力を取得する
- [ ] 3.2 プロンプトテンプレートに知識・秘密整合性の維持を明示する(enforcement は checker 側だが、prompting 要求として明記する)
- [ ] 3.3 mock provider を用いた決定的テスト(同一 seed で同一出力)を作成する
- [ ] 3.4 スキーマ不一致時のリトライ・エラー伝播をテストする

## 4. World Simulator

- [ ] 4.1 `living_narrative.agents.world_simulator` に時間経過・パラメータドリフト候補・勢力行動候補の生成ロジックを実装する
- [ ] 4.2 random-engine の weighted table を用いた背景イベント候補生成を実装する
- [ ] 4.3 全出力候補への `visibility` 付与を実装し、欠落時に検証エラーとするテストを作成する
- [ ] 4.4 mock provider + 固定 seed での決定的テストを作成する

## 5. Conflict Resolver

- [ ] 5.1 `living_narrative.agents.conflict_resolver` に行動候補 + イベント候補のマージロジックを実装する
- [ ] 5.2 `target_id` が一致する候補同士/排他的結果の衝突検出ロジックを実装する
- [ ] 5.3 design.md D4 の順序ポリシー(そのターンに directive を持つキャラクターの全候補を優先 → active_characters 順 → 背景イベント)を実装する
- [ ] 5.4 検出された衝突全件に対する random-engine への roll 要求を実装する(D121: 例外なし、決定的除外ルールは対象外)
- [ ] 5.5 resolved event(state-model Event 準拠、元候補の追跡可能性、roll で解決した event への `roll_ids` 記録)の生成を実装する
- [ ] 5.6 衝突検出・順序・roll 連携のテストを作成する

## 6. State Manager

- [ ] 6.1 `living_narrative.agents.state_manager` に resolved events → state diff 候補生成ロジックを実装する(D113: turn-pipeline の BuildDiff スロットの実装として登録する)
- [ ] 6.2 `source_event` を持たない変更候補の生成時拒否と `rejected_changes` への記録を実装する
- [ ] 6.3 `reveal_control`(must-not-reveal)によりマークされた事実を reader_state へ昇格する変更候補の除外と `rejected_changes` への記録を実装する
- [ ] 6.4 現在状態に対する diff 変更の検証(存在しない id 参照等)と失敗時の `rejected_changes` への理由記録を実装する
- [ ] 6.5 拒否ケース・正常ケースのテスト(`rejected_changes` の内容検証、reveal_control 除外ケースを含む)を作成する

## 7. Turn Pipeline スロット統合

- [ ] 7.1 add-turn-pipeline の Simulate/Act/Resolve/BuildDiff スロットを Context Builder/Character Agent/World Simulator/Conflict Resolver/State Manager の実装で置き換え、Check スロットを Checker フレームワークの実装で置き換える(D113: State Manager は BuildDiff スロットの実装として登録する)
- [ ] 7.2 各コンポーネントの入出力を turn artifact `agent_io/` へ保存する処理を実装する
- [ ] 7.3 途中失敗時の部分 artifact 保存を確認するテストを作成する

## 8. Checker フレームワーク

- [ ] 8.1 `living_narrative.safety` に checker レジストリ(D108 準拠、辞書ベース)を実装する
- [ ] 8.2 finding モデル(checker名/severity/message/related ids)を定義する
- [ ] 8.3 severity `error` によるブロッキングフラグ算出ロジックを実装する
- [ ] 8.4 `checks.yaml` への findings 永続化を実装する
- [ ] 8.5 レジストリ解決・ブロッキングフラグ・永続化のテストを作成する

## 9. Leak Checker

- [ ] 9.1 gm_vault fact id の機械的検出ロジックを実装する
- [ ] 9.2 hidden_facts / 他キャラクター secrets・private_mind テキストの正規化部分文字列一致検出ロジックを実装する
- [ ] 9.3 任意の LLM ベース漏洩評価(真偽値パラメータで opt-in、既定 warn)を実装する
- [ ] 9.4 各検出ロジックのテスト(漏洩あり/なし/パラフレーズで検出されないケース)を作成する

## 10. Continuity Checker

- [ ] 10.1 不在キャラクター行動・非登場キャラクター発言・source_event なし knowledge 追加の検出ロジックを実装する
- [ ] 10.2 任意の LLM ベース canon 矛盾検査(真偽値パラメータで opt-in、既定 warn)を実装する
- [ ] 10.3 各検出ロジックのテストを作成する

## 11. E2E テスト

- [ ] 11.1 mock provider + 固定 seed による複数キャラクター・複数ターンの e2e モックターンテストを作成し、Context Builder → Character Agent → World Simulator → Conflict Resolver → State Manager → Checker の一連の流れが正しく動作し、agent_io/checks.yaml/state_diff.yaml が期待通り生成されることを検証する
- [ ] 11.2 意図的に漏洩・矛盾を仕込んだ fixture で checker が error 級 finding を返し auto-apply がブロックされることを確認する回帰テストを作成する
