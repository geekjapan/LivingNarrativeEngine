## ADDED Requirements

### Requirement: Provider Protocol
すべての LLM provider は `complete(messages, response_schema: type[BaseModel], **params) -> BaseModel` という単一のインタフェース(Protocol)を実装しなければならない (SHALL)。エンジン内の agent(Character Agent / World Simulator / Conflict Resolver / Intervention Interpreter 等)からの全 LLM 呼び出しはこのインタフェース経由でのみ行われなければならない (SHALL)。直接 `openai` SDK やその他の HTTP クライアントを agent コードから呼び出してはならない。呼び出し元は `**params` に `prompt_template_name`(str)を必須のキーワード引数として渡さなければならず (SHALL)、provider 実装はこの値を変更せず呼び出しメタデータへそのまま伝搬しなければならない (SHALL)。

#### Scenario: agent が provider protocol 経由で呼び出す
- **WHEN** 任意の agent が LLM 応答を必要とする
- **THEN** その agent は provider の `complete(messages, response_schema, prompt_template_name=..., **params)` のみを呼び出し、戻り値として `response_schema` のインスタンスを受け取る

### Requirement: LLM プロファイル解決
llm-provider capability は、binding key(spec-foundation D122: `narrator` | `world_simulator` | `conflict_resolver` | `state_manager` | `checker` | `interpreter` | `character_default` | `character:<char_id>`)と project 設定(`llm`・任意の `llm_profiles`・任意の `llm_bindings`。add-project-foundation のスキーマで定義)を入力とし、解決済みプロファイル(`llm` と同スキーマ)を返す resolver 関数を提供しなければならない(SHALL)。解決順序は次の通りでなければならない(SHALL、D122): binding key が `character:<char_id>` の場合、`llm_bindings["character:<char_id>"]` → `llm_bindings["character_default"]` → 既定 `llm` の順に最初に見つかったプロファイルを採用する。binding key がそれ以外のロールの場合、`llm_bindings["<role>"]` → 既定 `llm` の順に最初に見つかったプロファイルを採用する。解決された各プロファイルに対応する provider インスタンスは独立して生成・利用可能でなければならず(SHALL)、1ターン内で複数の provider/model インスタンスが同時に有効であってもよい(MAY、D122)。

#### Scenario: キャラクター単位の binding が解決される
- **WHEN** `llm_bindings["character:char_002"]` が `"large_model"` に設定されている状態で binding key `character:char_002` を解決する
- **THEN** resolver は `llm_profiles["large_model"]` に対応するプロファイルを返す

#### Scenario: binding の無いロールは既定プロファイルへフォールバックする
- **WHEN** `llm_bindings` に `world_simulator` のエントリが存在しない状態で binding key `world_simulator` を解決する
- **THEN** resolver は既定の `llm` プロファイルを返す

### Requirement: Provider Registry
Provider は名前をキーとするレジストリ辞書に登録されなければならない (SHALL)(spec-foundation D108: 第1バッチはレジストリ辞書のみとし、plugin loader は実装しない)。`project.yaml` の `llm.provider` フィールドで指定された名前に対応する provider インスタンスが解決できなければならない (SHALL)。未登録の provider 名が指定された場合、エンジンは起動時に明確なエラーで失敗しなければならない (SHALL)。

#### Scenario: 未登録 provider 名の指定
- **WHEN** `project.yaml` の `llm.provider` に登録されていない名前が指定されている
- **THEN** システムは起動時(ターン実行前)にエラーを送出し、利用可能な provider 名の一覧を含むメッセージを表示する

### Requirement: 構造化出力の検証
Provider ラッパーは LLM の生応答から JSON を抽出し、指定された `response_schema`(Pydantic v2 モデル)でバリデーションしなければならない (SHALL)。バリデーションに成功した場合のみ、呼び出し元へ検証済みモデルインスタンスを返さなければならない (SHALL)。未検証のデータ(生 JSON・dict・部分的にのみ検証されたオブジェクト)を呼び出し元へ返してはならない。

#### Scenario: スキーマ準拠の応答を1回で検証成功
- **WHEN** LLM の応答がそのまま `response_schema` のバリデーションを通過する
- **THEN** `complete()` は検証済みの `response_schema` インスタンスを返し、retry は発生しない

### Requirement: 検証失敗時の修正指示付き retry
JSON 抽出またはスキーマバリデーションが失敗した場合、provider ラッパーは元の `messages` の末尾に直前の応答本文(assistant ロール)とバリデーションエラー内容を含む修正指示(user ロール)を追加した `messages` で LLM 呼び出しを再試行しなければならない (SHALL)。retry は最大2回までとする(spec-foundation §8)。retry で追加されるこれらのメッセージは prompt hash の算出対象に含めてはならない (SHALL NOT)。

#### Scenario: 1回目の応答がスキーマ不一致で2回目に成功する
- **WHEN** 1回目の LLM 応答がスキーマバリデーションに失敗する
- **THEN** provider ラッパーはバリデーションエラー内容を含む修正指示付きメッセージで再度 LLM を呼び出し、2回目の応答がバリデーションに成功すればそのモデルインスタンスを返す

### Requirement: retry上限到達時の型付きエラー
最大2回の retry を消費してもスキーマバリデーションに成功しない場合、provider ラッパーは型付きの例外(例: `StructuredOutputError`)を送出しなければならない (SHALL)。この例外は発生元 provider・model・使用した response_schema 名・最後のバリデーションエラー内容を保持し、呼び出し元がターン失敗ステータスへマッピングする際に利用できる情報を提供しなければならない (SHALL)。具体的なターンステータス名へのマッピング規則は本 capability の責務外とする。

#### Scenario: 3回とも検証に失敗する
- **WHEN** 初回呼び出し + retry 2回の合計3回とも `response_schema` のバリデーションに失敗する
- **THEN** provider ラッパーは型付き例外を送出し、その例外は最後のバリデーションエラー内容と使用した schema 名を含む

### Requirement: Mock Provider の決定性
Mock provider は `(random_seed, response_schema, prompt hash)` の組み合わせから決定的にスキーマ準拠の値を生成しなければならない (SHALL)。同一の入力の組み合わせに対しては常に同一の出力を返さなければならない (SHALL)。この決定性は呼び出しがどの LLM プロファイル(D122)経由であっても保たれなければならず(SHALL)、プロファイル名・model 名は決定性の入力に含まれない。

#### Scenario: 同一入力からの再現
- **WHEN** 同一の `random_seed`・同一の `response_schema`・同一の prompt(同一 hash)で mock provider を2回呼び出す
- **THEN** 2回とも完全に同一の内容を持つ検証済みインスタンスが返る

#### Scenario: プロファイルが異なっても決定性が保たれる
- **WHEN** 同一の `random_seed`・同一の `response_schema`・同一の prompt(同一 hash)だが異なるプロファイル(異なる model 名)を指定して mock provider を2回呼び出す
- **THEN** 2回とも完全に同一の内容を持つ検証済みインスタンスが返る

### Requirement: prompt hash の算出方法
prompt hash は、`complete()` に渡された初回呼び出し時点の `messages`(retry で追加される修正指示メッセージを含まない)を、キーをソートし余分な空白を含まない正規化 JSON としてシリアライズした文字列に対する SHA-256 の16進ダイジェストでなければならない (SHALL)。プロンプトテンプレートの文言や入力データが変化すれば prompt hash も必然的に変化し、scripted response の fixture はプロンプト内容の変更のたびに更新が必要になる。

#### Scenario: prompt hash がテンプレート変更で変わる
- **WHEN** 同一の入力データで、プロンプトテンプレートの文言のみが異なる状態で2回 `complete()` を呼び出す
- **THEN** 2回の呼び出しで算出される prompt hash は異なる値になる

### Requirement: Mock Provider の scripted response
Mock provider はテスト fixture からロードした scripted/canned response を、`response_schema` の名前と prompt hash の組み合わせ(`random_seed` には依存しない)をキーとして優先的に返せなければならない (SHALL)。scripted response が存在しないキーでは、決定的なデフォルト生成(schema 駆動の plausible な値)にフォールバックしなければならない (SHALL)。scripted response がそれ自体スキーマ検証に失敗した場合、mock provider は retry を行わず、fixture 設定エラーとして即座に型付き例外を送出しなければならない (SHALL)。

#### Scenario: fixture に一致する scripted response がある
- **WHEN** テスト fixture が特定のキー(schema 名 + prompt hash)に対する canned response を定義している
- **THEN** mock provider はデフォルト生成ではなく、その canned response をスキーマ検証した上で返す

#### Scenario: scripted response がスキーマ不一致の場合
- **WHEN** fixture 中の scripted response が対応する `response_schema` のバリデーションに失敗する
- **THEN** mock provider は retry を行わず、fixture 設定エラーを示す型付き例外を即座に送出する

### Requirement: ネットワーク非依存のテスト実行
本 capability に属する全テストスイートおよびエンジン全体の smoke test は、mock provider のみを用いてネットワークアクセスなしに実行可能でなければならない (SHALL)。

#### Scenario: ネットワーク遮断下でのテスト実行
- **WHEN** ネットワークアクセスが利用できない環境で `pytest`(llm-provider 関連テスト)を実行する
- **THEN** すべてのテストが mock provider のみで成功する

### Requirement: OpenAI 互換 Provider の設定
OpenAI 互換 provider は `openai` SDK を用い、`base_url` を設定可能にすることで OpenAI API 本体・Ollama・LM Studio のいずれにも接続できなければならない (SHALL)。`api_key` は環境変数からのみ取得しなければならない (SHALL)。`project.yaml` やコード中に直接 `api_key` を記述する経路をサポートしてはならない。リクエストタイムアウトは `project.yaml` の `llm.timeout_seconds`(add-project-foundation のスキーマで定義される任意フィールド、未指定時の既定値30秒)から取得し、設定可能でなければならない (SHALL)。

#### Scenario: base_url を切り替えて別エンドポイントに接続する
- **WHEN** `project.yaml` の `llm.base_url` に Ollama のローカルエンドポイントが設定されている
- **THEN** OpenAI 互換 provider はコード変更なしにそのエンドポイントへリクエストを送信する

### Requirement: 一時的な接続エラーの retry
OpenAI 互換 provider は接続エラーまたはタイムアウトが発生した場合、バックオフを伴い最大2回まで transient retry を行わなければならない (SHALL)。retry を使い切っても解決しない場合は型付き例外を送出しなければならない (SHALL)。

#### Scenario: 接続エラー後に retry で成功する
- **WHEN** 1回目のリクエストが接続タイムアウトで失敗する
- **THEN** provider はバックオフの後に再試行し、2回目が成功すればそのレスポンスを通常どおり処理する

#### Scenario: 全ての retry を使い切っても失敗する
- **WHEN** 初回 + retry 2回の合計3回すべてが接続エラーまたはタイムアウトになる
- **THEN** provider は型付き例外を送出し、生の接続例外の詳細(秘密情報を含む可能性のある部分を除く)を呼び出し元へ伝える

### Requirement: 呼び出しメタデータの記録
すべての LLM 呼び出しは、model 名・所要時間・token 使用量(provider から取得可能な場合)・prompt テンプレート名・prompt hash を含む呼び出しメタデータを記録し、呼び出し元が取得できるようにしなければならない (SHALL)。このメタデータは turn `meta.yaml`(spec-foundation §6)へ供給できる形式でなければならない。呼び出しが LLM プロファイル解決(D122)を経由した場合、メタデータには解決された binding key に対応するプロファイル名も追加で含まれなければならない(SHALL)。受け渡し機構として、provider ラッパーは呼び出しごとに構造化された `CallMetadata`(Pydantic モデル)を生成し、呼び出し元が provider ラッパー構築時に注入する recorder(`CallMetadata` を受け取る callable / Protocol)へ通知しなければならない(SHALL)。`complete()` の戻り値は検証済みモデルインスタンスのままとし、メタデータのためにシグネチャを変更してはならない(MUST NOT)。recorder への通知は、成功時だけでなく型付き例外(`StructuredOutputError`・transport エラー)の送出時にも、その時点までに判明している情報で行われなければならない(SHALL、meta.yaml が失敗ターンの呼び出しコストも記録できるようにするため)。

#### Scenario: 呼び出し後にメタデータが取得できる
- **WHEN** recorder を注入した provider の `complete()` 呼び出しが完了する(成功・retry を含む)
- **THEN** 注入した recorder に model 名・所要時間・prompt テンプレート名・prompt hash を含む `CallMetadata` が通知され、token 使用量が provider から取得できた場合はそれも含まれる

#### Scenario: 失敗した呼び出しのメタデータも通知される
- **WHEN** recorder を注入した provider の `complete()` が retry 上限到達で型付き例外を送出する
- **THEN** 例外送出前に recorder へ `CallMetadata` が通知され、実際に行われた全リクエスト分の所要時間(および取得できた token 使用量)が含まれる

#### Scenario: プロファイル解決経由の呼び出しでプロファイル名が記録される
- **WHEN** binding key `character:char_001` を解決して得たプロファイルで `complete()` を呼び出す
- **THEN** 呼び出しメタデータには解決されたプロファイル名が model 名と併せて含まれる

### Requirement: 秘密情報の非露出
`api_key` を含む秘密情報は、ログ出力・保存される artifact・例外メッセージのいずれにも一切出現してはならない (SHALL NOT)。

#### Scenario: 認証エラー発生時にログへ api_key が出力されない
- **WHEN** OpenAI 互換 provider への認証が `api_key` の誤りで失敗する
- **THEN** 送出される例外メッセージおよびログ出力には `api_key` の値が含まれない

### Requirement: Prompt の記録
Provider ラッパーは `project.yaml` の `llm.prompt_recording`(add-project-foundation のスキーマで定義される任意フィールド、`full` | `hash_only`、既定 `full`)に従い、既定(`full`)ではターン artifact に prompt 全文を保存しなければならない (SHALL)(private workspace 前提)。`hash_only` の場合は prompt 全文の代わりに hash のみを保存しなければならない (SHALL)。

#### Scenario: 既定設定で prompt 全文が保存される
- **WHEN** `project.yaml` の `llm.prompt_recording` が未指定または `full`(既定)の状態で LLM 呼び出しを行う
- **THEN** ターン artifact には送信した prompt の全文とその hash が保存される

#### Scenario: hash-only 設定で全文が保存されない
- **WHEN** `project.yaml` の `llm.prompt_recording` が `hash_only` に設定されている
- **THEN** ターン artifact には prompt の hash のみが保存され、全文は保存されない
