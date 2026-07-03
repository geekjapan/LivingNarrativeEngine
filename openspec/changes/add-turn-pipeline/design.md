# Design: add-turn-pipeline

## Context

state-model / random-engine / llm-provider の3 capability が揃った時点で、これらを spec-foundation §6 の
8 フェーズ順序に組み立てる layer が存在しない。`add-agent-runtime` が本格的な Character Agent / World Simulator /
Conflict Resolver を実装する前に、フェーズ間の入出力契約・artifact 形式・失敗処理・スロットの差し替え点を
固定しておく必要がある。本 change は、その骨格を mock provider で end-to-end に動く形で先に作る。

## Goals

- spec-foundation §6 の8フェーズを実行順序どおりに駆動する driver。
- Simulate/Act/Resolve/Check を Protocol ベースで差し替え可能にする(agent-runtime への置き換えを阻害しない)。
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

### D2: スロットは Protocol + 辞書レジストリ(D108 準拠、plugin loader は作らない)

Simulate / Act / Resolve / Check の各スロットは `typing.Protocol` で入出力の形を定義し、実装は名前キーの辞書に登録する。TurnPipeline はレジストリから該当スロットを取得して呼び出すのみで、実装クラスを直接 import しない。

- 根拠: spec-foundation D108 に準拠。add-agent-runtime が組み込みスロットを本実装に差し替える際、TurnPipeline 自体のコード変更を不要にする。
- 代替案: 抽象基底クラス(ABC)継承 — Protocol は構造的部分型のためテスト用スタブ実装が書きやすく、既存クラス階層に縛られない。ABC は不要な継承関係を強制するため不採用。

### D3: スロットの入出力は Pydantic モデルで型付けする

各スロットの入力(TurnContext の一部)・出力(候補イベント、行動候補、resolved events、checks 等)は Pydantic v2 モデルとして定義し、artifact の YAML シリアライズと直接対応させる。

- 根拠: spec-foundation §2 でスキーマ正本は Pydantic v2 と確定済み(D105)。artifact の形と in-memory の形を分離すると変換コードが二重管理になる。
- 代替案: dict ベースの緩い契約 — 実装は速いがスロット差し替え時の契約崩壊を検知できない。型検証の恩恵を捨てるため不採用。

### D4: commit-mode はプロジェクト設定の単純な二値フラグとして実装し、session-autonomy が置き換える前提を明示する

Commit フェーズの apply/pending 判断は `project.yaml` (または turn 実行時オプション)の `commit_mode: auto | review` のみで決める。stop condition・autonomy level・reader 側の確認要求などは一切見ない。

- 根拠: `add-session-autonomy` 未実装の段階でも Commit フェーズを動かす必要がある(依存関係上 turn-pipeline が先行するため)。二値フラグは spec-foundation §6 の「apply または review 待ち」を満たす最小実装。
- 移行経路: `add-session-autonomy` は本フラグを直接参照する呼び出し元を、autonomy level・stop condition 評価結果を渡す形に置き換える。TurnPipeline 側のインターフェース(Commit フェーズが「apply するか否かの bool」を受け取る)は変えず、判断ロジックの供給元だけを差し替える設計にしておく。
- 代替案: 本 change で暫定的に stop condition の一部(企画書 §10.6 のリスト)を先取り実装する — スコープ逸脱であり add-session-autonomy の重複実装になるため不採用。

### D5: Narrator は turn-pipeline と同一 change で提供するが、独立 capability として spec を分離する

`narration` は `turn-pipeline` とは別の capability spec ファイルに分離するが、依存関係・実装タイミングが同一のため同じ change にまとめる。

- 根拠: Narrate フェーズは turn-pipeline の1フェーズだが、可視性制約(spec-foundation §4.3 不変条件2)・renderer 拡張性(D108)という独立した設計上の関心事を持つため、将来 renderer を追加する change(Phase 6+)がこの capability だけを差分変更できるよう分離しておく。
- 代替案: turn-pipeline spec に Narrate フェーズの要件として統合 — capability の境界が曖昧になり、将来の renderer 追加 change が turn-pipeline 全体を re-spec することになるため不採用。

## Risks & Trade-offs

- [Risk] 同期実装のまま実LLMに切り替えると、複数キャラクター運用時に企画書 §11.1 の応答性目標を満たせない可能性がある。
  → Mitigation: 本 change では mock provider 前提のみを保証対象とし、Open Question として明記。Phase 2 性能作業で並列化を再評価する。
- [Risk] Protocol ベースのスロット契約が緩すぎると、add-agent-runtime の本実装で契約違反(例: visibility 未付与)が実行時まで検出されない。
  → Mitigation: スロット入出力を Pydantic モデルで型付けし(D3)、Check フェーズ・テストで visibility 必須フィールドの欠落を検出できるようにする。
- [Risk] commit-mode フラグが session-autonomy 導入後も残存し、二重の判断経路になる。
  → Mitigation: D4 で移行経路を設計時点から明記し、add-session-autonomy の proposal.md でこのフラグの置き換えを明示的な Modified Capability として扱う想定にする。

## Open Questions

- 実LLM運用時の並列化戦略(D1 参照)は Phase 2 性能作業で決定する。第1バッチをブロックしない。
