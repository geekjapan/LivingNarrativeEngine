# Design: add-llm-provider

## Context

すべての agent 呼び出しは LLM を介するが、agent がスキーマ不一致の応答をそのまま扱うと後続のパイプライン(state diff 生成・narration・checker)が壊れる。また実 LLM への依存はテストの決定性・CI 実行速度・API コストを損なう。本 change は provider 抽象・構造化出力の検証パイプライン・決定的 mock を先に固定し、以降の全 change(`add-turn-pipeline` 以降)が実 LLM なしでも動作を検証できる基盤を作る。

## Goals

- agent コードが provider 実装の詳細(SDK・エンドポイント形式)を一切知らずに済む単一インタフェースを提供する。
- 検証されていない LLM 出力が pipeline に流れ込むことを構造的に防ぐ。
- mock provider により、CI・smoke test・回帰テストが完全にネットワーク非依存かつ決定的に実行できる。
- 秘密情報(api_key)がいかなる artifact・ログにも漏れない。

## Non-Goals

- LiteLLM 等のマルチプロバイダ抽象ライブラリの導入。
- ストリーミング応答・部分応答のインクリメンタル処理。
- 複数モデル間のルーティング/フォールバック戦略。
- コスト予算管理・使用量の上限制御(Phase 9)。
- 非同期(async)実行(下記 Open Questions 参照)。

## Decisions

### D104(再掲・適用): `openai` SDK + 設定可能な `base_url`、LiteLLM 不採用
- **決定**: LLM client は `openai` SDK を1実装のみ用い、`base_url` を設定で切り替えることで OpenAI API 本体・Ollama・LM Studio をカバーする。
- **理由**: 対象がいずれも OpenAI 互換 API を提供しており、1実装で要件を満たせる。LiteLLM 等の抽象化層は本バッチの要件(単一 SDK・単一プロトコル対応で十分)に対して過剰であり、依存を増やすだけで恩恵が薄い(YAGNI)。
- **代替案**: LiteLLM 採用 → 複数ベンダー間の細かな差異(function calling 形式等)を吸収できるが、第1バッチでは OpenAI 互換 API のみを対象とするため不要な抽象化コストになる。不採用。

### Mock provider の生成戦略
- **決定**: mock provider の値生成は3段階で解決する。(1) テスト fixture に scripted response(識別子: schema 名 + prompt hash)があればそれを最優先で使用。(2) なければ `response_schema` の型情報(Pydantic の field 定義: 型・制約・デフォルト)から plausible なデフォルト値を機械的に構築する。(3) `random_seed` を用いてその値に決定的なバリエーション(文字列の suffix・数値のシード由来のオフセット等)を加える。
- **理由**: schema 駆動のデフォルト生成により、新しい response_schema を追加しても mock provider 側の追加実装なしに動作する(DRY)。scripted response による上書きで、特定シナリオ(異常系・特定の物語展開)を要求するテストにも対応できる。
- **代替案**: LLM 呼び出しを毎回録画/再生する VCR 方式 → 実 LLM 呼び出しの録画が必要になり、スキーマ変更のたびに録画し直すコストが発生する。第1バッチでは不採用。

### 同期(sync)のみの API(バッチ1)
- **決定**: `complete()` は同期関数として実装する。async 版は本 change では提供しない。
- **理由**: 第1バッチの turn pipeline は agent を逐次実行する設計であり(spec-foundation §6 の8フェーズは順次処理)、並列 agent 実行の要件が現時点で存在しない。async化は使われない抽象化になる(YAGNI)。
- **代替案**: 最初から `async def complete()` で実装 → 将来の並列化に備えられるが、pytest 側のモック実装や呼び出し元コードが複雑化し、現時点で恩恵を受ける呼び出し元が存在しない。Open Question として保留。

## Risks & Trade-offs

- [Risk] mock provider の schema 駆動デフォルト生成が、複雑な `Field` 制約(カスタム validator・相互依存フィールド)を持つ schema に対して有効な値を生成できない可能性がある → Mitigation: 生成失敗時は明確なエラーメッセージ付きで fail し、scripted response での明示的な上書きを促す。全 agent 応答 schema に対する mock 生成成功テストを `add-agent-runtime` 側で追加する前提とする。
- [Risk] `openai` SDK のバージョン差異により、Ollama/LM Studio 側の互換性が完全でない(function calling 非対応等)場合がある → Mitigation: 構造化出力は JSON 抽出 + Pydantic 検証というテキストベースの経路を主とし、SDK のネイティブ structured output 機能への依存を最小限にする。
- [Risk] token 使用量が provider によっては取得できない(一部の OpenAI 互換実装) → Mitigation: メタデータの token 使用量フィールドは optional とし、取得不能時は `None` を許容する。

## Open Questions

- **async API の要否**: 第1バッチでは同期のみとするが、Phase 2 で並列 agent 実行(例: 複数キャラクターの行動候補を並列生成)によるレイテンシ改善が必要になった場合、`complete()` の async 版または async ラッパーの追加を検討する。ユーザー確認待ち(ブロッキングではない)。
