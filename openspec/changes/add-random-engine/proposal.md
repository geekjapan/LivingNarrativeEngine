## Why

物語の進行には「制御された不確実性」が必要である(企画書 §5.3)。ターンパイプラインの Resolve フェーズ(spec-foundation §6)や後続の agent-runtime / intervention change がダイス判定・確率判定・ランダムイベント選択を必要とするため、それらより先に、決定的かつ再現可能な乱数基盤を単独 capability として用意する。

## What Changes

- `project.random_seed`(文字列)から決定的 RNG を初期化する仕組みを追加する。
- roll ごとに通番(project 内 sequence)を採番し、seed + 消費済み roll 数から RNG 状態を再構築できるようにする(resume/replay 対応)。
- ダイス記法パーサー `NdM` `NdM+K` `NdM-K`(N≤100, M≤1000)を追加する。省略可能な target 比較(結果値≥target で success)にも対応する。
- 確率判定(base_chance + named modifiers → final_chance を [0,100] にクランプ → d100 roll → success/failure)を追加する。
- weighted event table(重み付きエントリからの選択。条件評価は呼び出し側の責務)を追加する。
- 全 roll をターン artifact `rolls.yaml` に `roll_NNNN`(project 全体通番)として永続化する。
- reroll / GM override を、元 roll を `supersedes` で参照する新規 roll レコードとして記録する仕組みを追加する(履歴は上書きしない)。

## Capabilities

### New Capabilities

- `random-engine`: seed からの決定的 RNG 初期化、ダイス記法パース、確率判定、weighted table 選択、roll ログ永続化、reroll/override 履歴管理を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- TRPG 用ダイスルールモジュール(キャラクターシート連動、判定難易度テーブル等)は Phase 7 の対象であり本 change に含めない。
- 戦闘解決・エンカウンターデザインは対象外。
- weighted table のエントリ条件(condition)の評価ロジックは対象外。本 change は「呼び出し側が絞り込んだ eligible entries から選ぶ」ことのみを担う。
- 確率判定・weighted table の重み/修正値を決める上位ロジック(誰がどんな modifier を渡すか)は agent-runtime / turn-pipeline 側の責務であり対象外。

## Dependencies

- `add-project-foundation`(`project.yaml` の `random_seed` フィールド、workspace レイアウト、turn artifact ディレクトリ規約に依存)。

## Impact

- 新規コード: `src/living_narrative/random/`(`engine.py` `dice.py` `tables.py` 相当。企画書 §18.3 のディレクトリ構成に準拠)。
- 新規 artifact: 各 `workspace/runs/turn_NNNN/rolls.yaml`。
- 依存する将来 change: `add-turn-pipeline`(Resolve フェーズでの roll 実行・meta.yaml への rng 消費数記録)、`add-agent-runtime`(判定の呼び出し元)、`add-intervention`(dice_roll_request / GM override の実行経路)。
