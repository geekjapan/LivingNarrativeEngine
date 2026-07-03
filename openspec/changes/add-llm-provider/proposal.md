# Proposal: add-llm-provider

## Why

すべての agent(Character Agent / World Simulator / Conflict Resolver / Intervention Interpreter 等)は LLM 呼び出しを構造化出力として受け取る必要があるが、現時点で provider 抽象・構造化出力の検証・決定的な mock 実装が存在しない。`add-turn-pipeline` 以降のすべての change はこの capability に依存するため、`add-state-model` の次に単独で成立する形で実装する。

## What Changes

- Provider protocol `complete(messages, response_schema: type[BaseModel], **params) -> BaseModel` を定義し、provider を名前キーのレジストリ辞書に登録する(D108: plugin loader は作らない)。
- LLM プロファイル resolver を実装する(spec-foundation D122): binding key(`narrator` | `world_simulator` | `conflict_resolver` | `state_manager` | `checker` | `interpreter` | `character_default` | `character:<char_id>`)と project 設定(`llm`・`llm_profiles`・`llm_bindings`)から解決済みプロファイルを返す。1ターン内で複数 provider/model インスタンスの同時利用をサポートする。呼び出しメタデータには解決されたプロファイル名を追加で記録し、mock provider の決定性はプロファイルが異なっても保たれる。
- 構造化出力の共通ラッパーを実装する: LLM 応答から JSON を抽出 → Pydantic でバリデーション → 失敗時はバリデーションエラー内容を含む修正指示付きで最大2回まで retry → それでも失敗したら型付き例外を送出する(未検証データを決して返さない)。
- Mock provider を実装する: `(seed, schema, prompt hash)` から決定的にスキーマ準拠の値を生成する。テスト fixture からロードした scripted/canned response で特定シナリオを再現できる。全テストスイートおよび smoke test はネットワークなしで mock provider のみで実行可能とする。
- OpenAI 互換 provider を実装する: `openai` SDK + 設定可能な `base_url`(OpenAI API 本体・Ollama・LM Studio を1実装で担う)。`api_key` は環境変数からのみ取得する。接続/タイムアウトエラーは最大2回のバックオフ付き transient retry の後、型付き例外を送出する。リクエストタイムアウトは `project.yaml` の `llm.timeout_seconds`(add-project-foundation のスキーマ定義、既定30秒)から取得する。
- 呼び出しごとのメタデータ(model 名・所要時間・token 使用量(取得できる場合)・prompt テンプレート名・prompt hash)を記録し、turn `meta.yaml`(spec-foundation §6)へ供給できる形で公開する。
- 秘密情報衛生: `api_key` がログ・artifact・例外メッセージのいずれにも一切出現しないことを保証する。
- prompt 記録: `project.yaml` の `llm.prompt_recording`(add-project-foundation のスキーマ定義、`full` | `hash_only`、既定 `full`)に従い、既定でターン artifact に prompt 全文を保存する(private workspace 前提)。`hash_only` の場合は hash のみ保存する。

## Capabilities

### New Capabilities
- `llm-provider`: provider 抽象・レジストリ・構造化出力検証・mock provider・OpenAI 互換 provider・呼び出しメタデータ記録を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- LiteLLM の採用(spec-foundation D104 により不採用)。
- ストリーミング応答。
- 複数モデルの動的ルーティング/フォールバック戦略(失敗時の自動切替等)。静的な binding key → プロファイル解決(D122)は本 change の範囲に含まれる。
- コスト予算管理(Phase 9)。
- 画像・音声生成 provider。
- 非同期(async)API(本 change ではバッチ1として同期のみ。design.md の Open Questions を参照)。

## Dependencies

- `add-project-foundation`(project.yaml の `llm(provider, model, base_url)` 設定・workspace レイアウト・パッケージ土台に依存)。

## Impact

- 新規: `src/living_narrative/llm/`(protocol, registry, structured_output, mock provider, openai-compatible provider, metadata 型)、`tests/llm/`、テスト fixture(scripted response 用 YAML/JSON)。
- 影響を受ける既存コード: なし(greenfield)。
- 依存パッケージ追加: `openai`(実行時)。
