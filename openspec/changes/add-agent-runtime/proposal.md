# Proposal: add-agent-runtime

## Why

`add-turn-pipeline` はフェーズ順序と artifact 契約のみを定義し、Simulate/Act/Resolve/Check の各スロットは最小実装で埋められている。物語世界を実際に「動かす」ための知能 — スコープを守ったキャラクター行動生成、世界進行、衝突解決、状態差分生成 — と、それが情報を漏らさないことを検査する仕組みがなければ、本プロダクトの核となる価値(状態ファーストの介入型ナラティブ)は成立しない。

## What Changes

- `Context Builder` を追加し、spec-foundation §4.3 の不変条件を満たす agent 種別ごとの最小コンテキスト(Character Agent / World Simulator・State Manager)を `WorldStateBundle` から構築する(Narrator 用コンテキスト構築は `add-turn-pipeline` が既に提供しており対象外)。
- コンテキストサイズ制御として、直近 N 件のイベントのみを含める単純な切り詰めルールを実装する(memory summary は Phase 5 のため対象外)。
- `Character Agent` を追加し、スコープ済みコンテキストを入力に、行動候補(action/dialogue/inner_reaction)・感情変化候補・目標更新候補を visibility 付きで出力する。
- `World Simulator` を追加し、時間経過・世界パラメータドリフト候補・勢力行動候補・random-engine の weighted table を用いた背景イベント候補を出力する。
- `Conflict Resolver` を追加し、キャラクター行動候補と世界イベント候補をマージし、同一対象・排他的結果の衝突を検出し、検出した衝突は例外なく random-engine に判定を要求し(D121)、順序付けられた resolved event 列(state-model の Event 形式、roll で解決した event には `roll_ids` を付与)を生成する。
- `State Manager` を追加し、resolved event 列から state diff 候補(state-model の StateDiff 形式)を生成する。現在状態に対して検証し、`source_event` を持たない変更は生成時点で拒否する。当該ターンで確定した `reveal_control`(must-not-reveal)により reader 可視への昇格が禁じられた事実を reader_state へ昇格させる変更候補も同様に除外し、`rejected_changes` に記録する。
- 上記5コンポーネントの入出力を turn artifact の `agent_io/` 配下にすべて記録する。
- これらの実装で `add-turn-pipeline` が定義した Simulate/Act/Resolve/BuildDiff スロットの組み込み最小実装を置き換える(Context Builder は各スロット実装が共通に用いる純粋関数であり、それ自体はスロットではない)。State Manager は BuildDiff スロットの実装として登録される(D113): 入力は resolved events + 当該ターンの intervention + 全状態、出力は state diff 候補。Commit は非スロットの固定ロジックとして、BuildDiff(State Manager)の出力を state-model の apply インターフェースへ渡す。
- `Checker` フレームワークを追加し、`add-turn-pipeline` が定義した Check スロットの組み込み最小実装(no-op)を置き換える: checker はレジストリ登録され(D108: レジストリ辞書、plugin loader は作らない)、finding(checker名/severity/message/related ids)を返す。severity `error` は auto-apply をブロックし stop_for_review を要求する。
- `Leak Checker`(MVP 範囲)を追加する: narration・reader 可視イベントに対する機械的検査(gm_vault fact id・hidden_facts テキスト・他キャラクターの private_mind/secrets テキストの正規化部分文字列一致)、および任意の LLM ベース漏洩評価(既定 warn 級のヒューリスティックとして明示)。
- `Continuity Checker`(MVP 範囲)を追加する: resolved events / diff を canon と突き合わせる機械的な構造データ検査(死亡・不在キャラクターのシーン行動、非登場キャラクターの発言、`source_event` を持たない knowledge 追加)、および任意の LLM ベース canon 矛盾検査(既定 warn 級)。
- checker 実行結果を turn artifact `checks.yaml`(findings リスト)として永続化する。

## Capabilities

### New Capabilities
- `agent-runtime`: Context Builder / Character Agent / World Simulator / Conflict Resolver / State Manager を提供し、turn pipeline のスロットを実装で埋める。
- `consistency-checks`: checker フレームワーク、Leak Checker、Continuity Checker(いずれも MVP 範囲)を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- memory summary・relationship graph analytics(Phase 5)。
- Director / GM-assistant agent。
- 複数キャラクターの並列実行(本 change は逐次実行のみを扱う)。
- pacing checker・character consistency checker・repeated phrase checker・stale plot checker(Phase 5)。
- checker の停止処理そのもの(stop_for_review への配線)は `session-autonomy` capability の責務であり、本 change は finding の生成とブロッキングフラグの契約のみを提供する。
- LLM ベースの leak/continuity 検査の高精度化(パラフレーズ検出等)。

## Dependencies

- `add-turn-pipeline`(本 change が実装で置き換えるスロットの定義元。推移的に `add-state-model` / `add-random-engine` / `add-llm-provider` にも依存)。

## Impact

- 新規パッケージ `living_narrative.agents`(context_builder / character / world_simulator / conflict_resolver / state_manager のサブモジュール)。
- 新規パッケージ `living_narrative.safety`(checker レジストリ / leak_check / continuity_check)。
- `tests/agents/` および `tests/safety/` を新規追加(mock provider + fixture worldstate による決定的テスト)。
- 新規依存パッケージ追加なし。
