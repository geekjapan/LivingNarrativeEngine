## add-cli-and-sample — Grill残課題 (20260703)

### Q1. rollの reader可視性を判定する手段が存在せず、export-replayのlogスタイルroll要約フィルタが実装不能
- **対象**: `export-replay/spec.md` Requirement「reader可視性の遵守」「logスタイル出力」、および `add-random-engine/specs/random-engine/spec.md` の Roll ログ要件
- **なぜ重要**: export-replay の「reader可視性の遵守」要件は「narration.md本文、およびreader可視なintervention/roll/diffの要約に限られなければならない(SHALL)」と定め、logスタイルは「roll の要約」を注釈として出力しなければならない(SHALL)としている。intervention は `visibility` フィールドを持ち(intervention capability)、state diff の change も `visibility` を持つ(spec-foundation §5.1)ため、どちらもreader可視判定が可能。しかし roll レコード(spec-foundation §7、add-random-engine spec、企画書§14.9)は `id`/`type`/`dice`/`target`/`result_value`/`outcome`/`consequences`/`supersedes` のみを持ち、`visibility` フィールドが定義されていない。実装者は「どの roll が reader 可視か」を判定する根拠を一切持たない。
- **自己調査**: `add-random-engine/specs/random-engine/spec.md` 全文、`docs/project_plan.md` §14.9、spec-foundation §7 を確認したが、いずれも roll に visibility 概念を持たせていない。この欠落は add-random-engine(既に確定済みの先行 change)の責務であり、add-cli-and-sample の files のみでは roll スキーマへの `visibility` 追加はできない(cross-cutting)。
- **検討した選択肢**: A) roll に `visibility` フィールドを追加する add-random-engine への修正を提案する(roll発生源であるContested行動・イベント候補のvisibilityを継承させる)。 B) roll の可視性を「その roll が紐づく resolved event / state diff change の visibility」から間接的に導出する規則を export-replay 側で定義する(roll → event の追跡情報が現状 spec 上に存在するか要確認)。 C) 第1バッチでは roll 要約を常に全件出力する(visibility フィルタを roll には適用しない)ことを明示的な仕様上の例外として認める。
- **推奨案**: B が本筋(roll はほぼ必ず resolved event 経由で reader 可視性が決まるため)だが、roll → event の逆引き参照が spec 上定義されていないため、まずは A(add-random-engine への visibility 追加提案)を優先しつつ、当面の代替として C(全件出力・ヒューリスティックな注記なし)を明示的な既知の制約として design.md に記載するのが最小コストで smoke test をブロックしない。
- **不足インプット**: roll に visibility を追加すべきか(add-random-engine への修正 change が必要)、それとも export-replay 側で「reader可視なroll」を暫定的に「全件」または「対応するeventのvisibilityから導出」と定義してよいか、ユーザー判断が必要。
- **Status**: Resolved — D121: Event.roll_ids 経由で reader 可視 roll を導出 (openspec/changes/add-state-model/, openspec/changes/add-cli-and-sample/)

### Q2. ターンステータス(applied/pending_review/stopped_for_review/failed)の永続化場所が未定義で、export-replayのギャップ処理が実装不能
- **対象**: `export-replay/spec.md` Requirement「turn artifactからのreplay.md組み立て」「失敗・停止ターンのギャップ処理」、および `add-turn-pipeline/specs/turn-pipeline/spec.md` Requirement「ターンステータスモデル」
- **なぜ重要**: export-replay は各ターンを `applied`/`pending_review`/`stopped_for_review`/`failed` のいずれかとして扱い分ける(appliedのみ本文を含め、それ以外はギャッププレースホルダにする)ことが SHALL 要件になっている。しかし turn-pipeline spec の「ターンステータスモデル」要件は「ステータスは...そのターンのartifactのみから判別可能でなければならない」と述べるのみで、どのファイル・どのフィールドにステータス値が書き込まれるかを一切specifyしていない(`meta.yaml` の内容一覧にも status フィールドは含まれていない)。export-replay(本 change)はこの turn-pipeline 側の未定義箇所に依存しており、cli-and-sample 側だけでは読み込み対象ファイル/フィールドを確定できない。
- **自己調査**: `add-turn-pipeline/specs/turn-pipeline/spec.md` 全文、`add-turn-pipeline/specs/narration/spec.md`(narration.md のフロントマターに `visibility: reader` はあるが turn status は含まれない)を確認。turn status の書き込み先ファイルは spec 上どこにも明記されていない。turn-pipeline は add-cli-and-sample より前の change であり、cross-cutting なため本 change のみでは解決不能。
- **検討した選択肢**: A) turn-pipeline 側に `status.yaml`(または `meta.yaml` へのフィールド追加)を要求する修正を提案する。 B) `state_diff.yaml` の有無・内容(適用済みか否かのフラグ)から間接的に status を推定する規則を export-replay 側で定義する。 C) `review.yaml`(session-autonomy が定義)の有無から判定する。
- **推奨案**: A が最も明確(1ファイル/1フィールドの追加で全 capability から一貫して読める)。B/C は「diff はあるが未適用」と「diffがそもそも無い(介入なしターン)」を区別できない、または pending_review と stopped_for_review の区別に review.yaml 単独では不十分な可能性があり、暫定手段としては脆い。
- **不足インプット**: turn-pipeline 側の `meta.yaml` に `status` フィールドを追加するか、専用ファイルを新設するか。add-turn-pipeline への修正 change が必要かどうかの判断。
- **Status**: Resolved — D111: meta.yaml の status フィールドが正本 (openspec/changes/add-turn-pipeline/)

### Q3. `init` コマンドの仕様所有権が project-workspace(add-project-foundation)と cli(add-cli-and-sample)に分裂しており、proposal.md の Modified Capabilities に project-workspace が挙がっていない
- **対象**: `add-cli-and-sample/proposal.md`「Modified Capabilities: (なし)」、`add-cli-and-sample/specs/cli/spec.md` Requirement「`init` によるプロジェクト新規作成とテンプレート検証」、`add-project-foundation/specs/project-workspace/spec.md` Requirement「init コマンドによるプロジェクト作成」「既存ディレクトリへの上書き拒否」
- **なぜ重要**: 同一のCLIコマンド `living-narrative init` の契約が、2つの異なる capability(project-workspace / cli)に分散して記述されている。project-workspace 側は「`--title` のみ必須、内容は後続changeが本格テンプレートで置き換え可能な最小構成でよい」とする一方、cli 側は `--genre`/`--tone`/`--template`/`--output` を含む完全な契約と未登録テンプレート名のエラー処理を独自に規定する。両者は直接矛盾はしていない(cli側がproject-workspace側の最小契約を上位互換的に拡張している)が、proposal.md の Modified Capabilities は「(なし)」であり、project-workspace が挙げられていない。将来 `openspec archive` で正本スペックへマージする際、`init` の契約が `project-workspace/spec.md` と `cli/spec.md` の2ファイルに分裂したまま残ることになり、どちらが正本かが曖昧になる。
- **自己調査**: `add-project-foundation/specs/project-workspace/spec.md` 全文、`add-cli-and-sample/proposal.md`・`specs/cli/spec.md` を確認。project-workspace 側の文言(「後続changeが本格的なテンプレートで置き換え可能な最小の空ワールド構成でよい」)は将来の拡張を明示的に許容しているが、それが「cli capability として独立に再規定してよい」という意味なのか、「project-workspace への MODIFIED Requirement として上書きされるべき」という意味なのかは spec 上判別できない。add-project-foundation は自分が編集できない他 change のため、この判断を本 change 単独で確定できない。
- **検討した選択肢**: A) `add-cli-and-sample/proposal.md` の Modified Capabilities に `project-workspace` を追加し、`specs/project-workspace/spec.md` に `init` Requirement の MODIFIED delta(`--genre`/`--tone`/`--template` を含む完全版で置換)を追加する。 B) 現状維持(cli capability による additive 拡張とし、Modified 宣言はしない)。project-workspace 側の「後続changeが置き換え可能」という文言を「additive拡張を許容する」という意味だと解釈する。
- **推奨案**: B が最小変更で smoke test 等をブロックしないが、A の方が openspec のスペックマージ規約上は正しい可能性が高い。どちらを採るかは openspec のスペック運用方針(capability の正本をどう1つに保つか)に関わるため、本 change 単独では断定しない。
- **不足インプット**: openspec のスペックアーカイブ運用として、後続changeが先行changeの同一CLIコマンドを拡張する場合に Modified Capabilities 宣言を必須とするかどうかのユーザー方針確認。
- **Status**: Resolved — project-workspace を Modified Capabilities に追加し init を MODIFIED delta 化 (openspec/changes/add-cli-and-sample/)

### Q4. MVP成功条件「10〜20ターン進行できる」に対し、smoke testは10ターン固定のみを検証する
- **対象**: `proposal.md`(企画書§21.4引用)、`specs/cli/spec.md` Requirement「サンプル世界での10ターンスモークテスト」、`docs/project_plan.md` §21.4/§26.1
- **なぜ重要**: 企画書§21.4/§26.1のMVP成功条件は「10〜20ターン進行できる」だが、本changeの回帰テストは10ターン固定であり、11〜20ターン目でのみ顕在化しうる問題(例: turn番号のゼロパディング境界、artifactディレクトリの蓄積、コンテキスト切り詰めの累積効果等)は回帰テストで捕捉されない。design.md はこれを「10ターンをレンジの下限として固定する」設計判断として扱っているが、上限側(20ターン)の動作を実証しない選択について明示的な理由付けがない。
- **自己調査**: `design.md` の Goals/Decisions を確認したが、「10ターン」を選んだ理由(下限確認で十分/上限確認は別capabilityの責務等)は明記されていない。10ターンを超えた際に構造的に破綻しうる箇所(turn_NNNNのゼロパディングは9999まで許容、agent-runtimeのコンテキスト直近N件切り詰めは10ターンでも20ターンでも同じロジック)を確認した限り、10ターンと20ターンで質的に異なる挙動をする既知の要因はspec上見当たらない。
- **検討した選択肢**: A) smoke testを20ターンに拡張する(mock providerのみで実行時間・コストへの影響は小さい)。 B) 現状の10ターンのまま、「10は範囲下限の確認であり上限固有のリスクはない」という判断根拠をdesign.mdに一文追記する。 C) 別途20ターンのオプション/低頻度smoke testを追加する。
- **推奨案**: B(最小変更)を基本としつつ、余力があればA(20ターンへの拡張)を採用するのが安全側。ただしテスト実行時間・CI負荷とのトレードオフのため、ユーザー確認が望ましい。
- **不足インプット**: 20ターンまでの smoke test 拡張が許容できるCI実行時間か、10ターンで打ち切ることを正式なMVP解釈として確定してよいかのユーザー判断。
- **Status**: Resolved — smoke test を20ターンに拡張 (openspec/changes/add-cli-and-sample/)
