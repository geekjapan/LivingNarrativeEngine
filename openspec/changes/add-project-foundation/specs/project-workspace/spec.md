## ADDED Requirements

### Requirement: リポジトリ開発ツールチェーン
プロジェクトは `uv` で管理する `pyproject.toml` を持ち、パッケージ `living_narrative` を `src/` レイアウトで配置しなければならない(SHALL)。Python の要求バージョンは 3.12 以上でなければならない(SHALL)。dev 依存として `pytest` と `ruff` を含めなければならない(SHALL)。

#### Scenario: uv sync でセットアップできる
- **WHEN** リポジトリを clone した直後に `uv sync` を実行する
- **THEN** `living_narrative` パッケージおよび `pytest`・`ruff` を含む dev 依存が解決され、コマンドがエラーなく完了する

#### Scenario: ruff によるフォーマット・lint 検証
- **WHEN** `ruff check .` および `ruff format --check .` を実行する
- **THEN** 未整形・lint 違反があれば非ゼロ終了コードで報告される

### Requirement: CI パイプライン
リポジトリは GitHub Actions のワークフローを持ち、push および pull request で `uv sync` → `ruff check` → `ruff format --check` → `pytest` を順に実行しなければならない(SHALL)。いずれかのステップが失敗した場合、後続ステップの成否によらず CI 全体を失敗として報告しなければならない(SHALL)。

#### Scenario: CI がテスト失敗を検知する
- **WHEN** pull request に `pytest` が失敗するコード変更が含まれる
- **THEN** CI ワークフローは失敗ステータスを報告する

### Requirement: project.yaml スキーマ
`project.yaml` のスキーマは Pydantic v2 モデルを単一正本としなければならない(SHALL、spec-foundation D105)。モデルは少なくとも次のフィールドを持たなければならない(SHALL): `id`, `title`, `genre`, `tone`, `language`(既定値 `"ja"`), `autonomy_level`, `user_mode`, `random_seed`, `renderer`, `llm`(`provider`, `model`, 任意の `base_url`, 任意の `timeout_seconds`(既定値 `30`), 任意の `prompt_recording`(`full` | `hash_only` の enum、既定値 `"full"`)), `workspace`(`root`, `state`, `runs`, `exports` の各パス)。`llm.timeout_seconds`/`llm.prompt_recording` は `add-llm-provider` capability が LLM 呼び出し時に消費する設定値であり(spec-foundation D118)、本 change ではスキーマフィールドとして保持するのみで消費ロジックは実装しない。`project.yaml` ファイルの YAML ルートはこれらのフィールドを直接キーとして持たなければならない(SHALL)。企画書 Appendix B の `project:` というインデントはドキュメント上のグルーピング表記であり、実ファイルではラップキーとしない。`id` は spec-foundation §3 の `<type>_<zero-padded番号>` 規約の対象外の自由形式文字列であり(project id はこの規約が列挙する ID 種別に含まれない)、フォーマット検証を課してはならない(SHALL NOT)。`autonomy_level` は spec-foundation §3 の `autonomy_level` 正準 enum(`manual`/`assist`/`auto`/`watch`/`god`)の、`user_mode` は同じく `user_mode` 正準 enum(`watcher`/`assistant_gm`/`full_gm`/`author`/`player_character`/`god`)の、いずれかの値でなければならない(SHALL)。モデルは任意で `llm_profiles`(プロファイル名をキー、値は `llm` と同スキーマとする辞書、既定値は空辞書)と `llm_bindings`(binding key をキー、`llm_profiles` 内のプロファイル名を値とする辞書、既定値は空辞書)を持ってよい(MAY、spec-foundation D122)。`llm_bindings` の各キーは `narrator` | `world_simulator` | `conflict_resolver` | `state_manager` | `checker` | `interpreter` | `character_default` | `character:<char_id>`(`<char_id>` は spec-foundation §3 の `char_<zero-padded番号>` 形式)のいずれかのパターンに一致しなければならず(SHALL)、一致しないキーはロード時検証エラーとしなければならない(SHALL)。`llm_bindings` の値が `llm_profiles` に存在しないプロファイル名を参照している場合、ロード時検証エラーとしなければならない(SHALL)。

#### Scenario: 最小構成の project.yaml を読み込む
- **WHEN** 企画書 Appendix B の `project:` インデント内容をラップキー無しでトップレベルに展開した `project.yaml` を読み込む
- **THEN** 全フィールドが Pydantic モデルにマッピングされ、`language` 未指定の場合は `"ja"` が補完される

#### Scenario: 未定義プロファイルへの binding は検証エラーになる
- **WHEN** `llm_bindings` が `llm_profiles` に定義されていないプロファイル名を参照する `project.yaml` を読み込む
- **THEN** ロードは失敗し、エラーレポートには当該 binding key と未定義のプロファイル名を含む項目が含まれる

### Requirement: project.yaml ロード時検証とエラー集約
`project.yaml` のロードはスキーマ検証を伴わなければならない(SHALL)。検証エラーが複数存在する場合、最初の1件で停止せず、対象ファイルパス・フィールド名・理由を含むエラーの一覧として集約して報告しなければならない(SHALL)。未知フィールドはロードを失敗させてはならず、警告として扱わなければならない(SHALL)。

#### Scenario: 複数フィールドが不正な project.yaml
- **WHEN** `random_seed` が欠落し、かつ `autonomy_level` が許容値外の `project.yaml` を読み込む
- **THEN** ロードは失敗し、エラーレポートには両方のフィールドについてファイルパス・フィールド名・理由を含む項目が含まれる

#### Scenario: 未知フィールドを含む project.yaml
- **WHEN** スキーマに存在しないフィールドを含む `project.yaml` を読み込む
- **THEN** ロードは成功し、未知フィールドについての警告が出力される

### Requirement: workspace ディレクトリレイアウト
プロジェクトの workspace は企画書 Appendix C に準拠したディレクトリ構成を持たなければならない(SHALL): `workspace/state/`(`world.yaml`, `canon.yaml`, `reader_state.yaml`, `gm_vault.yaml`, `scenes/`, `characters/`, `relationships.yaml`, `timeline.yaml`, `unresolved_threads.yaml`)、`workspace/runs/`、`workspace/exports/`。

#### Scenario: init 後のディレクトリ構成
- **WHEN** `living-narrative init` でプロジェクトを新規作成する
- **THEN** 生成された workspace は上記の全ディレクトリ・ファイルを含む

### Requirement: init コマンドによるプロジェクト作成
`living-narrative init` コマンドは、必須オプション(少なくとも `--title`)を受け取り、指定した出力先にプロジェクトディレクトリと `project.yaml`、workspace 一式を生成しなければならない(SHALL)。生成する state ファイルの内容は、後続 change が本格的なテンプレートで置き換え可能な最小の空ワールド構成でよい。`--title` 以外の `project.yaml` フィールドは次の固定既定値を用いなければならない(SHALL): `id` は `--title` から生成する ASCII 英数字とハイフンのみの slug(ASCII で表現できない場合は固定文字列 `"project"` にフォールバックする)、`genre`/`tone` は空文字列、`autonomy_level` は `"manual"`、`user_mode` は `"assistant_gm"`(`watcher` は `manual` と組み合わせると add-session-autonomy の Mode × Level 正規化により警告付きで `watch` へ変換されるため、正規化されない有効な既定ペアを用いる)、`random_seed` は実行のたびに一意な自動生成値、`renderer` は `"novel"`、`llm.provider` は `"mock"`、`llm.model` は `"mock-v1"`、`workspace.root`/`state`/`runs`/`exports` は企画書 Appendix B と同じ相対パス(`workspace`, `workspace/state`, `workspace/runs`, `workspace/exports`)。

#### Scenario: 新規プロジェクトの作成
- **WHEN** 存在しない出力先パスを指定して `living-narrative init --title "霧の駅"` を実行する
- **THEN** コマンドは成功し、`project.yaml` の `title` に `"霧の駅"` が設定され、`llm.provider` に `"mock"` が設定され、workspace レイアウトが規定どおり生成される

### Requirement: 既存ディレクトリへの上書き拒否
`living-narrative init` は、出力先ディレクトリが既に存在し中身が空でない場合、生成処理を実行せずエラーで終了しなければならない(SHALL)。

#### Scenario: 既存の空でないディレクトリへの init
- **WHEN** 既にファイルが存在する出力先パスを指定して `living-narrative init` を実行する
- **THEN** コマンドはエラーを報告し、既存ファイルを変更・削除しない

### Requirement: プロジェクト読み込み API
プロジェクト読み込み API は、`project.yaml` のファイルパスを起点として `workspace` 配下の各パス(`root`/`state`/`runs`/`exports`)を解決しなければならない(SHALL)。ワークスペースパスが `project.yaml` に対する相対パスとして指定されている場合、`project.yaml` の所在ディレクトリを基準に解決しなければならない(SHALL)。

#### Scenario: 相対パスによる workspace 解決
- **WHEN** `project.yaml` が `projects/mist_station/project.yaml` に存在し、`workspace.state` が相対パス `workspace/state` と指定されている
- **THEN** 解決後の state パスは `projects/mist_station/workspace/state` となる

### Requirement: 必須 state ファイルの存在確認
プロジェクト読み込み API は、workspace レイアウトで定義された必須ファイル(`world.yaml`, `canon.yaml`, `reader_state.yaml`, `gm_vault.yaml`, `relationships.yaml`, `timeline.yaml`, `unresolved_threads.yaml`)の存在を確認しなければならない(SHALL)。欠落しているファイルがある場合、欠落ファイルの一覧を含む検証レポートを返さなければならない(SHALL)。ファイル内容そのもののスキーマ検証(`add-state-model` の範囲)は行わない。

#### Scenario: state ファイルが一部欠落したプロジェクトの読み込み
- **WHEN** `gm_vault.yaml` が存在しない workspace を読み込む
- **THEN** 読み込みは失敗し、検証レポートに `gm_vault.yaml` の欠落が含まれる

### Requirement: 秘密情報の非露出
project 読み込み・`init` に関わるいかなるログ出力・例外メッセージ・エラーレポート・検証レポートも、`.env`/環境変数由来の API キー等の秘密情報の値を含んではならない(SHALL、spec-foundation §8)。本 change は `project.yaml` ロード時に環境変数から API キーを読み取ったり、その有無を検証したりする機能を実装しない(SHALL NOT)。LLM provider に対する API キーの取得元(環境変数のみ)・有無検証・接続時のエラー処理は `add-llm-provider` capability の責務である。

#### Scenario: llm 設定を含む project.yaml の検証エラー
- **WHEN** `llm.provider` 等のフィールド値が不正な `project.yaml` を読み込み、検証エラーレポートを生成する
- **THEN** エラーレポートには当該フィールドの検証エラー理由のみが含まれ、`.env`/環境変数から取得されうる API キー等の秘密情報の値は一切含まれない
