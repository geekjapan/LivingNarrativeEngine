## add-llm-provider — Grill残課題 (20260703)

### Q1. retry上限到達時の型付き例外はターンステータス `stop_for_review` と `failed` のどちらにマッピングされるべきか
- **対象**: `docs/spec-foundation.md` §6(失敗ポリシー: 「schema 不一致 → 最大2回 retry → stop_for_review」)と `openspec/changes/add-turn-pipeline/specs/turn-pipeline/spec.md` の Requirement「スキーマ不一致時のretry委譲」(「llm-provider が最終的に型付き例外を送出した場合...ターンステータスを `failed` にしなければならない」)
- **なぜ重要**: 両者は同じ事象(LLM構造化出力の retry 上限到達)に対して異なるターンステータスを規定しており、turn-pipeline 実装者がどちらに従うべきか一意に決まらない。add-cli-and-sample の10ターン smoke test は「10ターンが `failed` にならず完走すること」を検証条件にしており、`stop_for_review` と `failed` の扱いの違いは smoke test の合否にも影響しうる。
- **自己調査**: `docs/spec-foundation.md` §6・§9(決定ログ)、`openspec/changes/add-turn-pipeline/specs/turn-pipeline/spec.md`、`openspec/changes/add-cli-and-sample/specs/cli/spec.md` を確認したが、spec-foundation を turn-pipeline 側が明示的に上書きした旨の記述は無く、単純な記述の不一致に見える。add-llm-provider は例外に情報を持たせる責務のみで、マッピング先の決定権は turn-pipeline / spec-foundation にあるため、本 change 側だけでは解決できない(add-llm-provider 側の該当 Requirement からは `stop_for_review` という固有名詞の記述を除去済み)。
- **検討した選択肢**: A) spec-foundation §6 を正とし、turn-pipeline 側を `stop_for_review` に修正する / B) turn-pipeline 側を正とし、spec-foundation §6 の文言を「retry 上限到達 → failed」に修正する / C) 両者を統合し、「schema 不一致は起動前提条件違反として即 `failed`、`stop_for_review` は Check フェーズの checker error 検出専用」と役割分担を明文化する
- **推奨案**: C。turn-pipeline 側は既に Check フェーズのエラー検出を `stopped_for_review` に明確に割り当てており(該当 spec.md 内で別 Requirement として存在)、LLM retry 失敗は「エージェントが構造化出力を生成できない」というより重い失敗であるため `failed` の方が turn-pipeline の設計と整合する。spec-foundation §6 の該当行を turn-pipeline の実際の挙動に合わせて修正するのが最小の変更で済む。
- **不足インプット**: spec-foundation §6 と add-turn-pipeline のどちらを正とするかのユーザー判断、および該当箇所の編集承認(add-llm-provider の変更範囲外)。
- **Status**: Resolved — D110: failed を正とし spec-foundation §6/§8 修正済み (docs/spec-foundation.md)。注: 本項の引用に現れる `stop_for_review` は修正前の spec-foundation §6 の旧表記をそのまま引用したものであり、正準のターンステータス enum 値は `stopped_for_review`(現行仕様に `stop_for_review` という状態は存在しない)

### Q2. turn `meta.yaml` は LLM 呼び出しの token 使用量を集約フィールドとして含めるべきか
- **対象**: `docs/spec-foundation.md` §6(`meta.yaml` の内容: 所要時間・LLM 呼び出し回数・model・prompt hash・rng 消費数)、`openspec/changes/add-turn-pipeline/specs/turn-pipeline/spec.md` の Requirement「meta.yaml の内容」(token 使用量への言及なし)、および本 change の Requirement「呼び出しメタデータの記録」(呼び出しごとに token 使用量を含める)
- **なぜ重要**: add-llm-provider は呼び出しごとの token 使用量を「turn meta.yaml へ供給できる形式」で公開する契約だが、meta.yaml の正本である turn-pipeline 側の必須フィールド一覧に token 使用量が存在しない。実装者は「meta.yaml に token 使用量の集約値(合計)を追加すべきか、それとも捨ててよいか」を判断できず、企画書 §24.4(コスト対策として token/cost tracking を挙げる)とも整合が取れているか不明。
- **自己調査**: `docs/spec-foundation.md` §6、`docs/project_plan.md` §24.4、`openspec/changes/add-turn-pipeline/specs/turn-pipeline/spec.md` の meta.yaml Requirement を確認。turn-pipeline 側の meta.yaml スキーマは add-turn-pipeline の責務であり、add-llm-provider からは追加・変更できない。
- **検討した選択肢**: A) turn-pipeline の meta.yaml 必須フィールドに「token 使用量合計(取得できた呼び出し分のみ集計、取得不能時は省略可)」を追加する / B) token 使用量は meta.yaml に含めず、各呼び出しの生メタデータ(agent_io 配下等)にのみ残す設計を明文化する / C) 現状のまま(turn-pipeline が meta.yaml 生成時に持っている情報から自由に取捨選択してよい、という暗黙の解釈)を維持する
- **推奨案**: A。企画書 §24.4 が token/cost tracking をコスト対策の一つに明記しており、meta.yaml がターンごとの唯一の集約 artifact であることを踏まえると、token 使用量(合計・取得不能呼び出しは無視)を meta.yaml の必須フィールドに追加するのが将来のコスト管理機能(Phase 9)にも接続しやすい。
- **不足インプット**: turn-pipeline 側の meta.yaml スキーマ拡張の要否・優先度についてのユーザー判断(add-turn-pipeline の変更範囲)。
- **Status**: Resolved — D111: meta.yaml に llm_tokens_total を正式追加 (openspec/changes/add-turn-pipeline/)

### Q3. `timeout`(接続タイムアウト)・prompt 全文/hash-only 切替フラグの設定はどこに置くか
- **対象**: 本 change の Requirement「OpenAI 互換 Provider の設定」(timeout を設定可能にする SHALL)・「Prompt の記録」(hash-only 切替フラグ SHALL)と、`openspec/changes/add-project-foundation/specs/project-workspace/spec.md` の Requirement「project.yaml スキーマ」(`llm` フィールドは `provider`・`model`・任意の `base_url` のみを列挙)
- **なぜ重要**: `project.yaml` の `llm` セクションのスキーマは add-project-foundation が正本として定義しており、そこには timeout・prompt 記録モードの置き場所が存在しない。実装者は (a) `llm.timeout_seconds` 等を project-workspace 側の Pydantic モデルに無断で追加する、(b) 環境変数や CLI フラグなど project.yaml 以外の経路に置く、のどちらかを独自判断することになり、`project.yaml` のフィールド名・置き場所が実装間で割れるリスクがある。project-workspace 側の「未知フィールドは警告のみで失敗しない」規則が `llm` サブオブジェクトのネストしたフィールドにも適用されるかどうかも spec からは読み取れない。
- **自己調査**: `openspec/changes/add-project-foundation/specs/project-workspace/spec.md` の「project.yaml スキーマ」「project.yaml ロード時検証とエラー集約」Requirement、`docs/spec-foundation.md` §5(project.yaml の `llm(provider,model,base_url)` という記載)を確認。add-project-foundation は本 change の依存元(下流ではなく前提)であり、add-llm-provider から project-workspace の Pydantic スキーマを拡張する権限も記述もない。本 change 側でタイムアウトの既定値(30秒)は自己解決したが、設定の「置き場所」(project.yaml のキー名か、それ以外か)は cross-cutting な未決事項として残る。
- **検討した選択肢**: A) `project.yaml` の `llm` に `timeout_seconds`(任意, 既定30)・`prompt_recording`(`full` | `hash_only`, 既定 `full`)を追加するよう add-project-foundation 側のスキーマを拡張する / B) これらは provider 実装のコンストラクタ引数・環境変数(例: `LLM_TIMEOUT_SECONDS`)としてのみ提供し、project.yaml には含めない / C) provider 登録時に渡す provider 固有設定辞書(project.yaml の `llm` 直下ではなく `llm.provider_options` のような自由形式フィールド)に格納する
- **推奨案**: A。project.yaml が唯一のプロジェクト設定正本であるという spec-foundation の設計方針(D103: 状態の正本はファイル)と整合し、`--base_url` 同様にプロジェクトごとに変えたい値であるため。ただし A を選ぶ場合は add-project-foundation 側のスキーマ更新が必須となる。
- **不足インプット**: add-project-foundation の project.yaml スキーマを拡張してよいか(または既に固定済みで変更不可か)についてのユーザー判断。
- **Status**: Resolved — D118: llm.timeout_seconds / llm.prompt_recording を project.yaml に正式追加 (openspec/changes/add-project-foundation/)
