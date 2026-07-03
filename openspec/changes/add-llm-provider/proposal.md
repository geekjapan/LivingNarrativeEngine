# Proposal: add-llm-provider

## Why

すべての agent(Character Agent / World Simulator / Conflict Resolver / Intervention Interpreter 等)は LLM 呼び出しを構造化出力として受け取る必要があるが、現時点で provider 抽象・構造化出力の検証・決定的な mock 実装が存在しない。`add-turn-pipeline` 以降のすべての change はこの capability に依存するため、`add-state-model` の次に単独で成立する形で実装する。

## What Changes

- Provider protocol `complete(messages, response_schema: type[BaseModel], **params) -> BaseModel` を定義し、provider を名前キーのレジストリ辞書に登録する(D108: plugin loader は作らない)。
- 構造化出力の共通ラッパーを実装する: LLM 応答から JSON を抽出 → Pydantic でバリデーション → 失敗時はバリデーションエラー内容を含む修正指示付きで最大2回まで retry → それでも失敗したら型付き例外を送出する(未検証データを決して返さない)。
- Mock provider を実装する: `(seed, schema, prompt hash)` から決定的にスキーマ準拠の値を生成する。テスト fixture からロードした scripted/canned response で特定シナリオを再現できる。全テストスイートおよび smoke test はネットワークなしで mock provider のみで実行可能とする。
- OpenAI 互換 provider を実装する: `openai` SDK + 設定可能な `base_url`(OpenAI API 本体・Ollama・LM Studio を1実装で担う)。`api_key` は環境変数からのみ取得する。接続/タイムアウトエラーは最大2回のバックオフ付き transient retry の後、型付き例外を送出する。リクエストタイムアウトは設定可能にする。
- 呼び出しごとのメタデータ(model 名・所要時間・token 使用量(取得できる場合)・prompt テンプレート名・prompt hash)を記録し、turn `meta.yaml`(spec-foundation §6)へ供給できる形で公開する。
- 秘密情報衛生: `api_key` がログ・artifact・例外メッセージのいずれにも一切出現しないことを保証する。
- prompt 記録: 既定でターン artifact に prompt 全文を保存する(private workspace 前提)。設定フラグで hash のみ保存に切り替え可能にする。

## Capabilities

### New Capabilities
- `llm-provider`: provider 抽象・レジストリ・構造化出力検証・mock provider・OpenAI 互換 provider・呼び出しメタデータ記録を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- LiteLLM の採用(spec-foundation D104 により不採用)。
- ストリーミング応答。
- 複数モデルのルーティング/フォールバック戦略。
- コスト予算管理(Phase 9)。
- 画像・音声生成 provider。
- 非同期(async)API(本 change ではバッチ1として同期のみ。design.md の Open Questions を参照)。

## Dependencies

- `add-project-foundation`(project.yaml の `llm(provider, model, base_url)` 設定・workspace レイアウト・パッケージ土台に依存)。

## Impact

- 新規: `src/living_narrative/llm/`(protocol, registry, structured_output, mock provider, openai-compatible provider, metadata 型)、`tests/llm/`、テスト fixture(scripted response 用 YAML/JSON)。
- 影響を受ける既存コード: なし(greenfield)。
- 依存パッケージ追加: `openai`(実行時)。
