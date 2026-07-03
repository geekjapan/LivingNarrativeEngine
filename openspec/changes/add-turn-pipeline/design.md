# Design: add-turn-pipeline

## Context

state-model / random-engine / llm-provider の3 capability が揃った時点で、これらを spec-foundation §6 の
8 フェーズ順序に組み立てる layer が存在しない。`add-agent-runtime` が本格的な Character Agent / World Simulator /
Conflict Resolver を実装する前に、フェーズ間の入出力契約・artifact 形式・失敗処理・スロットの差し替え点を
固定しておく必要がある。本 change は、その骨格を mock provider で end-to-end に動く形で先に作る。

## Goals

- spec-foundation §6 の8フェーズを実行順序どおりに駆動する driver。
- Simulate/Act/Resolve/BuildDiff/Check を Protocol ベースで差し替え可能にする(agent-runtime への置き換えを阻害しない)。
- mock provider + 組み込み最小スロットだけで、性能目標(企画書 §11.1: mock turn 1秒未満)を満たす形でターンが完走する。
- 失敗時も再現性(企画書 §11.2)に必要な情報を含む部分 artifact を必ず残す。

## Non-Goals

- 本格的な agent 実装(add-agent-runtime)。
- intervention の自由文解釈(add-intervention)。
- autonomy レベル・stop condition・GM review gate の意思決定(add-session-autonomy)。

## Decisions

### D1: pipeline は同期・逐次関数呼び出しとして実装する(非同期・キューは導入しない)

8フェーズを1本のスレッド内で順に呼び出すだけの、素の逐次関数呼び出しとして実装する。async/await やジョブキューは導入しない。

- 根拠: mock provider での性能目標(1秒未満、企画書 §11.1)は同期実装で容易に満たせる。第1バッチは単一ユーザー・単一ターン実行が前提で、並列実行の要求が無い。YAGNI。
- 代替案: asyncio ベースの pipeline — 実LLM呼び出しの並列化(複数キャラクターの Act フェーズを並列に投げる等)に有利だが、現時点では要求が無く複雑性が見合わない。
- Open Question: 実LLM運用時、複数キャラクターの Act フェーズを並列化しないと企画書 §11.1 の「複数Agent + Check: 30〜90秒」目標を満たせない可能性がある。これは Phase 2 の性能作業で再評価する(本 change では同期のままでよいと判断)。

### D2: スロットは Protocol + 辞書レジストリ(D108/D113 準拠、plugin loader は作らない)

Simulate / Act / Resolve / BuildDiff / Check の5つのスロットは `typing.Protocol` で入出力の形を定義し、実装は名前キーの辞書に登録する。TurnPipeline はレジストリから該当スロットを取得して呼び出すのみで、実装クラスを直接 import しない。BuildDiff は resolved events・そのターンの intervention・全状態を入力に受け取り、state diff 候補を出力するスロットであり、その契約には reveal_control の must-not-reveal 制約の遵守(読者可視スコープへの昇格を阻止すること)を含む。Commit フェーズは Resolve/Narrate/Check の完了後に BuildDiff スロットを呼び出して diff 候補を取得し、その出力を commit-mode に従って state-model の apply へ渡すだけの固定ロジックであり、スロットとしては差し替え不可能である(D113)。

- 根拠: spec-foundation D108/D113 に準拠。add-agent-runtime の State Manager が BuildDiff の本実装を提供し、Commit フェーズ内部と State Manager による二重 diff 生成を排除する。
- 代替案: 抽象基底クラス(ABC)継承 — Protocol は構造的部分型のためテスト用スタブ実装が書きやすく、既存クラス階層に縛られない。ABC は不要な継承関係を強制するため不採用。

### D3: スロットの入出力は Pydantic モデルで型付けする

各スロットの入力(TurnContext の一部)・出力(候補イベント、行動候補、resolved events、checks 等)は Pydantic v2 モデルとして定義し、artifact の YAML シリアライズと直接対応させる。

- 根拠: spec-foundation §2 でスキーマ正本は Pydantic v2 と確定済み(D105)。artifact の形と in-memory の形を分離すると変換コードが二重管理になる。
- 代替案: dict ベースの緩い契約 — 実装は速いがスロット差し替え時の契約崩壊を検知できない。型検証の恩恵を捨てるため不採用。

### D4: commit-mode はターン実行 API のランタイムパラメータとして渡し、session-autonomy が置き換える前提を明示する

Commit フェーズの apply/pending 判断は、ターン実行 API 呼び出し単位のパラメータ `commit_mode: auto | review` のみで決める(D118: project.yaml のフィールドにはしない。将来 CLI フラグとして公開し、session-autonomy は autonomy_level/user_mode からこの値を計算して渡す)。stop condition・autonomy level・reader 側の確認要求などは一切見ない。Commit フェーズは BuildDiff スロット(D2/D113)の出力である state diff 候補を受け取り、commit_mode と Check フェーズの結果に基づいて state-model の apply へ渡すか pending に据え置くかを決めるだけであり、diff 自体は生成しない。

- 根拠: `add-session-autonomy` 未実装の段階でも Commit フェーズを動かす必要がある(依存関係上 turn-pipeline が先行するため)。ランタイムパラメータは spec-foundation §6 の「apply または review 待ち」を満たす最小実装であり、D118 のスキーマ汚染回避方針とも整合する。
- 移行経路: `add-session-autonomy` は本パラメータの供給元を、autonomy level・stop condition 評価結果から計算する形に置き換える。TurnPipeline 側のインターフェース(Commit フェーズが「apply するか否か」を決める commit_mode を受け取る)は変えず、供給元だけを差し替える設計にしておく。
- 代替案: 本 change で暫定的に stop condition の一部(企画書 §10.6 のリスト)を先取り実装する — スコープ逸脱であり add-session-autonomy の重複実装になるため不採用。

### D5: Narrator は turn-pipeline と同一 change で提供するが、独立 capability として spec を分離する

`narration` は `turn-pipeline` とは別の capability spec ファイルに分離するが、依存関係・実装タイミングが同一のため同じ change にまとめる。

- 根拠: Narrate フェーズは turn-pipeline の1フェーズだが、可視性制約(spec-foundation §4.3 不変条件2)・renderer 拡張性(D108)という独立した設計上の関心事を持つため、将来 renderer を追加する change(Phase 6+)がこの capability だけを差分変更できるよう分離しておく。
- 代替案: turn-pipeline spec に Narrate フェーズの要件として統合 — capability の境界が曖昧になり、将来の renderer 追加 change が turn-pipeline 全体を re-spec することになるため不採用。

### D6: `failed` ターン再実行は旧 artifact を discarded-dir へ退避し、ターン番号決定・退避ロジックを公開ユーティリティとして提供する(D112)

`failed` ターンを再実行する際、TurnPipeline は同じ `turn_NNNN` ディレクトリへの上書きではなく、旧ディレクトリを `turn_NNNN_discarded_<n>` へ退避してから新規に `turn_NNNN` ディレクトリを作成して実行する。そのターンの `rng_draws_consumed` 累積カウントには退避された旧試行分も合算する。次ターン番号決定ロジック(D111 の「最後に applied されたターン+1」)とこの退避ロジックは、TurnPipeline 内部専用の関数ではなく、モジュール外(`add-session-autonomy`)から呼び出し可能な公開ユーティリティとして実装する。

- 根拠: 同一ディレクトリへの上書きは過去の失敗試行の `rolls.yaml` 等を消去し監査可能性(spec-foundation §7)を損なう。`add-session-autonomy` の GM review gate が要求する `rerun_turn` 操作は、TurnPipeline の8フェーズ実行そのものは経由せず state-model の diff 適用 API を直接呼び出す設計(D4 の移行経路)だが、「旧ターン artifact を退避してターン番号を再利用する」という同じセマンティクスを必要とするため、TurnPipeline 内で一度実装したロジックを公開ユーティリティとして再利用させ、重複実装を避ける。
- 代替案: 退避ロジックを TurnPipeline 内部にのみ実装し、`add-session-autonomy` が独自に同等のロジックを再実装する — 監査可能性のロジックが2箇所に分散し、ディレクトリ命名規約の不整合リスクがあるため不採用。

## Risks & Trade-offs

- [Risk] 同期実装のまま実LLMに切り替えると、複数キャラクター運用時に企画書 §11.1 の応答性目標を満たせない可能性がある。
  → Mitigation: 本 change では mock provider 前提のみを保証対象とし、Open Question として明記。Phase 2 性能作業で並列化を再評価する。
- [Risk] Protocol ベースのスロット契約が緩すぎると、add-agent-runtime の本実装で契約違反(例: visibility 未付与)が実行時まで検出されない。
  → Mitigation: スロット入出力を Pydantic モデルで型付けし(D3)、Check フェーズ・テストで visibility 必須フィールドの欠落を検出できるようにする。
- [Risk] commit-mode ランタイムパラメータが session-autonomy 導入後も残存し、二重の判断経路になる。
  → Mitigation: D4 で移行経路を設計時点から明記し、add-session-autonomy の proposal.md でこのパラメータの供給元置き換えを明示的な Modified Capability として扱う想定にする。

## Open Questions

- 実LLM運用時の並列化戦略(D1 参照)は Phase 2 性能作業で決定する。第1バッチをブロックしない。
