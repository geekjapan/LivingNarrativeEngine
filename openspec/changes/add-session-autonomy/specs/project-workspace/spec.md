# project-workspace

## MODIFIED Requirements

### Requirement: project.yaml スキーマ
`project.yaml` のスキーマは Pydantic v2 モデルを単一正本としなければならない(SHALL、spec-foundation D105)。モデルは少なくとも次のフィールドを持たなければならない(SHALL): `id`, `title`, `genre`, `tone`, `language`(既定値 `"ja"`), `autonomy_level`, `user_mode`, `random_seed`, `renderer`, `llm`(`provider`, `model`, 任意の `base_url`, 任意の `timeout_seconds`(既定値 `30`), 任意の `prompt_recording`(`full` | `hash_only` の enum、既定値 `"full"`)), `workspace`(`root`, `state`, `runs`, `exports` の各パス)。`llm.timeout_seconds`/`llm.prompt_recording` は `add-llm-provider` capability が LLM 呼び出し時に消費する設定値であり(spec-foundation D118)、project-workspace はスキーマフィールドとして保持するのみで消費ロジックは実装しない。`project.yaml` ファイルの YAML ルートはこれらのフィールドを直接キーとして持たなければならない(SHALL)。企画書 Appendix B の `project:` というインデントはドキュメント上のグルーピング表記であり、実ファイルではラップキーとしない。`id` は spec-foundation §3 の `<type>_<zero-padded番号>` 規約の対象外の自由形式文字列であり(project id はこの規約が列挙する ID 種別に含まれない)、フォーマット検証を課してはならない(SHALL NOT)。`autonomy_level` は spec-foundation §3 の `autonomy_level` 正準 enum(`manual`/`assist`/`auto`/`watch`/`god`)の、`user_mode` は同じく `user_mode` 正準 enum(`watcher`/`assistant_gm`/`full_gm`/`author`/`player_character`/`god`)の、いずれかの値でなければならない(SHALL)。モデルは任意で `llm_profiles`(プロファイル名をキー、値は `llm` と同スキーマとする辞書、既定値は空辞書)と `llm_bindings`(binding key をキー、`llm_profiles` 内のプロファイル名を値とする辞書、既定値は空辞書)を持ってよい(MAY、spec-foundation D122)。`llm_bindings` の各キーは `narrator` | `world_simulator` | `conflict_resolver` | `state_manager` | `checker` | `interpreter` | `character_default` | `character:<char_id>`(`<char_id>` は spec-foundation §3 の `char_<zero-padded番号>` 形式)のいずれかのパターンに一致しなければならず(SHALL)、一致しないキーはロード時検証エラーとしなければならない(SHALL)。`llm_bindings` の値が `llm_profiles` に存在しないプロファイル名を参照している場合、ロード時検証エラーとしなければならない(SHALL)。

モデルは任意で `stop_conditions`(停止条件のプロジェクト設定。既定値は空辞書)を持ってよい(MAY)。`stop_conditions` の各キーは `stop_condition` を除く9つの停止条件名(`character_death` / `major_canon_change` / `relationship_threshold_crossing` / `major_secret_reveal` / `checker_error` / `leak_suspicion` / `heavy_roll_failure` / `scene_end` / `target_turn_count_reached`)のいずれかでなければならず(SHALL)、値は `enabled`(bool、既定値 `true`)と任意の `threshold`(整数)を持つオブジェクトでなければならない(SHALL)。上記9条件以外のキー(`stop_condition` を含む — ユーザーの明示的停止要求は無効化できない。spec-foundation D119)はロード時検証エラーとしなければならない(SHALL)。`threshold` は閾値を持つ条件(現時点では `relationship_threshold_crossing` のみ)に対してのみ指定でき(SHALL)、閾値を持たない条件に指定された場合はロード時検証エラーとしなければならない(SHALL)。project-workspace はこのフィールドをスキーマとして保持・検証するのみであり、消費(停止条件評価。未設定時の既定値の意味論を含む)は `session-autonomy` capability の Requirement「停止条件のプロジェクト設定」が正本である。

#### Scenario: 最小構成の project.yaml を読み込む
- **WHEN** 企画書 Appendix B の `project:` インデント内容をラップキー無しでトップレベルに展開した `project.yaml` を読み込む
- **THEN** 全フィールドが Pydantic モデルにマッピングされ、`language` 未指定の場合は `"ja"` が補完され、`stop_conditions` 未指定の場合は空辞書が補完される

#### Scenario: 未定義プロファイルへの binding は検証エラーになる
- **WHEN** `llm_bindings` が `llm_profiles` に定義されていないプロファイル名を参照する `project.yaml` を読み込む
- **THEN** ロードは失敗し、エラーレポートには当該 binding key と未定義のプロファイル名を含む項目が含まれる

#### Scenario: stop_conditions の有効な設定を読み込む
- **WHEN** `stop_conditions: {heavy_roll_failure: {enabled: false}, relationship_threshold_crossing: {threshold: 30}}` を含む `project.yaml` を読み込む
- **THEN** ロードは成功し、`heavy_roll_failure.enabled` は `false`、`relationship_threshold_crossing` は `enabled: true`(既定値)かつ `threshold: 30` としてマッピングされる

#### Scenario: stop_condition キーは検証エラーになる
- **WHEN** `stop_conditions: {stop_condition: {enabled: false}}` を含む `project.yaml` を読み込む
- **THEN** ロードは失敗し、エラーレポートには `stop_condition` は無効化できない旨(spec-foundation D119)を含む項目が含まれる
