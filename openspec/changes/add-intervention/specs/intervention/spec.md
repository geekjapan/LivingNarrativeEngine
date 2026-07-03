## ADDED Requirements

### Requirement: Intervention スキーマ
Intervention は企画書 §14.8 に準拠し、`id`(project 内一意、`int_NNNN` ゼロパディング通番、spec-foundation §3)、`turn`(発生ターン番号)、`user_role`(介入時点の `user_mode`。企画書 §8: `watcher` / `assistant_gm` / `full_gm` / `author` / `player_character` / `god`)、`type`、`target`、`content`(自由文または要約テキスト)、`constraints`(キー・バリューの追加制約)、`visibility`(spec-foundation §4.2 の enum)のフィールドを持たなければならない(SHALL)。`type` は企画書 §10.7 に列挙された15種(`scene_directive` `character_directive` `world_directive` `event_injection` `probability_bias` `tone_control` `pacing_control` `reveal_control` `hidden_truth_edit` `canon_edit` `dice_roll_request` `stop_condition` `scene_pivot` `relationship_edit` `memory_edit`)のいずれかでなければならない(SHALL)。`target` は spec-foundation §5.1 の StateDiff target enum(`world` / `character` / `scene` / `reader_state` / `canon` / `gm_vault` / `relationship`)に、dice_roll_request 用の `roll` を加えた集合の値と、対象を一意特定する任意の id を持たなければならない(SHALL)。Pydantic v2 モデルとしてロード時に検証されなければならない(SHALL、spec-foundation §5)。

#### Scenario: 正常なスキーマの Intervention が検証を通過する
- **WHEN** 全必須フィールドを満たす `type: world_directive` の Intervention データをロードする
- **THEN** バリデーションが成功し、型付き Intervention インスタンスが得られる

#### Scenario: 未知の type は拒否される
- **WHEN** `type` フィールドが15種のいずれにも一致しない値を持つ Intervention データをロードする
- **THEN** バリデーションエラーとなり、インスタンスは生成されない

### Requirement: Type 別ハンドリング状況の明示
Intervention システムは、各 `type` について「バッチ1で専用ルーティング・実行動作を持つ」か「`session-autonomy` capability など後段の消費先へ委譲する」か「受理・保存・agent への constraints 提示のみを行い専用ハンドラを持たない」かを、コード上で参照可能な形(例: type→handling-status のマッピング)として明示しなければならない(SHALL)。`scene_directive` `character_directive` `world_directive` `event_injection` `tone_control` `reveal_control` `dice_roll_request` `canon_edit` `hidden_truth_edit` の9種は本 change 内で専用ルーティングを持つ(SHALL)。`stop_condition` は本 change 内では独自の状態変更ロジックを持たないが(SHALL NOT)、`intervention.yaml` への保存を通じて `session-autonomy` capability の停止条件評価(10番目の停止条件として、Check→Commit の境界で全 autonomy レベル(watch/god を含む)において停止する。D119)に消費される、明示的な委譲先を持つ type として区別されなければならない(SHALL)。残る `probability_bias` `pacing_control` `scene_pivot` `relationship_edit` `memory_edit` の5種は専用ハンドラを持たない(SHALL NOT ルーティングエラーとして扱われてはならない — 正常に受理・保存され、関係する agent のコンテキストへ constraints として提示される)。

#### Scenario: 未ハンドルタイプの intervention は正常に保存される
- **WHEN** `type: memory_edit` の Intervention をパイプラインに投入する
- **THEN** エラーにはならず、`intervention.yaml` に保存され、専用の状態変更は発生しない

#### Scenario: 未ハンドルタイプが agent コンテキストへ constraints として提示される
- **WHEN** `type: pacing_control` の Intervention が存在するターンで Character Agent 用コンテキストを構築する
- **THEN** そのコンテキストには当該 intervention の `content` と `constraints` が制約情報として含まれる(状態への直接反映は伴わない)

#### Scenario: stop_condition は intervention.yaml に保存され session-autonomy に委譲される
- **WHEN** `type: stop_condition` の Intervention が確定する
- **THEN** `intervention.yaml` に保存され、本 change 内では専用の状態変更ロジックは実行されず、`session-autonomy` capability の停止条件評価に消費される委譲先として handling-status に明示される

### Requirement: Intervention Interpreter による自由文解釈
Intervention Interpreter は、ユーザーの自由文を入力として受け取り、llm-provider の構造化出力(spec-foundation §8、`complete(messages, response_schema)`)を用いて1件以上の Intervention を生成しなければならない(SHALL)。出力全体には、生成された Intervention 群とは別に、解釈全体に対する confidence(0.0〜1.0 の数値)と人間可読な解釈要約(interpretation summary)を含めなければならない(SHALL)。LLM に構造化出力させる各 Intervention 要素は `type`/`target`/`content`/`constraints`/`visibility` のみとし、`id`/`turn`/`user_role` は含めてはならない(SHALL NOT)。これらのフィールドは、呼び出し元がそのターンの実行コンテキスト(現在のターン番号・現在の `user_mode`・id 採番機構)から確定値を補完したうえで、正規の Intervention スキーマとして検証されなければならない(SHALL)。自由文の一部が既知の type にも属さないと判断された場合、Interpreter はその部分を黙って破棄してはならず(SHALL NOT)、`scene_directive` として `content` にそのまま保持したフォールバック Intervention を生成しなければならない(SHALL)。

#### Scenario: 単一自由文が複数 Intervention に分解される
- **WHEN** 「リナにはカイの様子がおかしいことに気づかせたい。ただし、カイの秘密はまだ明かさない」という自由文を Interpreter に渡す(企画書 §7.2 の例)
- **THEN** `character_directive`(対象: リナ)と `reveal_control`(カイの秘密を非開示)を含む2件以上の Intervention が生成され、confidence と interpretation summary が付与される

#### Scenario: 未分類の自由文断片は scene_directive にフォールバックする
- **WHEN** 自由文の一部がどの既知 type にも明確に分類できない
- **THEN** その部分は破棄されず、`type: scene_directive` の Intervention として元の文言を保持したまま生成される

### Requirement: 構造化直接入力パス
Intervention システムは、LLM Interpreter を経由せず、呼び出し元(CLI フラグやテストコード)が型付き Intervention フィールドを直接指定して Intervention を構築できる経路を提供しなければならない(SHALL)。呼び出し元が直接指定できるのは `type`/`target`/`content`/`constraints`/`visibility` のみであり、`id`/`turn`/`user_role` は Interpreter 経路と同一の規則で常にシステムが補完しなければならない(SHALL、呼び出し元がこれらを指定した場合でも上書きしてはならない)。この経路は Interpreter と同一のスキーマ検証・permission hook を適用しなければならない(SHALL)。

#### Scenario: 直接入力パスで Intervention を構築する
- **WHEN** 呼び出し元が `type` `target` `content` `constraints` を直接指定して Intervention 構築 API を呼ぶ
- **THEN** LLM 呼び出しを伴わずに、スキーマ検証済みの Intervention インスタンスが生成される

#### Scenario: 直接入力パスにも permission hook が適用される
- **WHEN** 直接入力パスで、現在の `user_mode` が許可されない type の Intervention を構築しようとする
- **THEN** Interpreter 経路と同様に型付き rejection が返され、Intervention は生成されない

### Requirement: Role Permission Hook
Intervention capability は、intervention 生成時(Interpreter 経由・直接入力経路のいずれも)に、プラガブルな許可判定関数(`type` と `user_mode` を入力に取り、外部から注入される permission table(データ、コード分岐ではない)を参照して許可可否を返す関数)を通して permission を強制しなければならない(SHALL)。この判定関数が intervention capability 自身のコードとしてハードコードしてよい制約は、普遍的不変条件として次のみに限られる(SHALL、SHALL NOT それ以外の type×user_mode 組み合わせを固定してはならない): `canon_edit` と `hidden_truth_edit` は `full_gm` または `god` の `user_mode` でなければ許可されない。それ以外の13種の type に対する許可 user_mode 集合の正本は `session-autonomy` capability が持つ(15種×6モードの完全な権限マトリクスは本 change の対象外)。`session-autonomy` capability から permission table が供給されない場合、intervention capability は既定の permission table として、上記の普遍的不変条件を除き全ての type×user_mode の組み合わせを許可しなければならない(SHALL、permissive デフォルト)。Intervention 生成時、判定関数が許可しない場合、システムは Intervention を生成せず、type・要求された user_mode・許可されている user_mode 集合(または違反した不変条件)を含む型付き rejection を返さなければならない(SHALL)。

#### Scenario: 許可されない user_mode での canon_edit は拒否される
- **WHEN** `user_mode: watcher` の状態で `type: canon_edit` の Intervention を生成しようとする
- **THEN** Intervention は生成されず、`canon_edit` には `full_gm`/`god` が必要である旨を含む型付き rejection が返される

#### Scenario: 許可された user_mode での canon_edit は生成される
- **WHEN** `user_mode: god` の状態で `type: canon_edit` の Intervention を生成しようとする
- **THEN** rejection は発生せず、Intervention が正常に生成される

### Requirement: パイプライン統合(Intervene フェーズ)
Intervention は spec-foundation §6 のフェーズ2(Intervene)で消費され、そのターンで確定した Intervention 群はターン artifact `intervention.yaml` に保存されなければならない(SHALL)。当該ターンに介入が無い場合、`intervention.yaml` は空の状態で保存されなければならない(SHALL、`add-turn-pipeline` の既定動作との後方互換)。

#### Scenario: 介入ありのターンで intervention.yaml が生成される
- **WHEN** あるターンで1件以上の Intervention が確定する
- **THEN** そのターンの `workspace/runs/turn_NNNN/intervention.yaml` に、確定した全 Intervention が記録される

#### Scenario: 介入なしのターンでも intervention.yaml は空で生成される
- **WHEN** あるターンでユーザーが介入しない
- **THEN** `intervention.yaml` は空(介入なし)の状態で生成され、後続フェーズは通常どおり進行する

### Requirement: Type 別ルーティング
確定した Intervention は type に応じて次のように実行主体へルーティングされなければならない(SHALL): `character_directive` は対象キャラクターのコンテキストのみに渡され、他キャラクターや Narrator のコンテキストには含まれてはならない(spec-foundation §4.3 準拠)。`world_directive` および `event_injection` は World Simulator へ渡される。`tone_control` および `reveal_control` は Narrator 制約として渡される。`dice_roll_request` は Conflict Resolver 経由で Random Engine の判定要求として渡される。`canon_edit` および `hidden_truth_edit` は State Manager 経由で直接 state diff エントリとして生成され、`visibility`(`canon` は canon 相当、`hidden_truth_edit` は `gm_only` 既定)が尊重されなければならない(SHALL、D107: state 変更は全て diff 経由)。`reveal_control` の Narrator 制約としての伝達は、Requirement「reveal_control の意味論」に定める BuildDiff スロット(spec-foundation §6 フェーズ8内、agent-runtime の State Manager 実装。D113)での Reader State 昇格制御を代替しない(SHALL NOT)。両者は独立した効果であり、いずれも実装されなければならない(SHALL)。

#### Scenario: character_directive は対象キャラクターにのみ渡される
- **WHEN** `char_002` を対象とする `character_directive` が確定したターンでコンテキストを構築する
- **THEN** `char_002` のコンテキストにその directive が含まれ、他のキャラクター・Narrator のコンテキストには含まれない

#### Scenario: canon_edit が state diff として生成される
- **WHEN** `type: canon_edit` の Intervention が State Manager に渡される
- **THEN** `source_event` として当該 intervention id を参照する state diff エントリ(target: `canon`)が生成され、Canon への直接書き換えは発生しない

#### Scenario: dice_roll_request が Random Engine 判定として実行される
- **WHEN** `type: dice_roll_request` の Intervention(例: 「2d6で7以上なら気づく」)が Resolve フェーズに渡される
- **THEN** Conflict Resolver は指定された条件で Random Engine に判定を要求し、結果が `rolls.yaml` に記録される

### Requirement: reveal_control の意味論
`reveal_control` Intervention は、対象事実を `must-not-reveal`(開示禁止)または `reveal-now`(即時開示)のいずれかとしてマークしなければならない(SHALL)。この強制点は spec-foundation §6 フェーズ8(Commit)内の BuildDiff スロット(agent-runtime の State Manager が実装。D113)であり、turn-pipeline 側に intervention 専用の Commit hook を追加してはならない(SHALL NOT)。`must-not-reveal` としてマークされた事実は、BuildDiff が生成する state diff 候補のうち、その事実を Reader State へ昇格させる change から除外されなければならない(SHALL)。`reveal-now` としてマークされた事実は、BuildDiff の出力として、その事実を Reader State へ昇格させる state diff 変更が emit されなければならない(SHALL)。Intervention capability の責務は BuildDiff が参照する制約データ(must-not-reveal / reveal-now マーク)を生成することのみであり、BuildDiff 自体の実装は agent-runtime capability の責務である(本 change に含まれない)。

#### Scenario: must-not-reveal が Reader State 昇格をブロックする
- **WHEN** ある事実に対して `reveal_control`(`must-not-reveal`)が確定しているターンで、その事実が reader 可視イベントの候補に含まれる
- **THEN** BuildDiff が生成する state diff 候補にその事実を Reader State へ昇格させる change は含まれない

#### Scenario: reveal-now が Reader State への即時昇格を発生させる
- **WHEN** ある GM Vault 内の事実に対して `reveal_control`(`reveal-now`)が確定している
- **THEN** BuildDiff の出力に、その事実を Reader State に追加する state diff 変更が含まれる

### Requirement: Intervention 履歴インデックス
プロジェクト全体で累積する Intervention 履歴インデックス(`interventions.yaml`)を、ターンをまたいで維持しなければならない(SHALL)。各エントリは intervention id・発生ターン・type・そのターンで生じた結果(event id / state diff id 等)への source reference・`superseded_by_rerun`(既定 `false`)フラグを持ち、任意の intervention について「何が実際に起きたか」を追跡可能にしなければならない(SHALL)。あるターンの intervention 群に対応するエントリは、そのターンの Commit フェーズ完了時点(spec-foundation §6 フェーズ8、event id と候補 state diff id の双方が確定した後)で、source reference を含めて一度だけ書き込まれなければならない(SHALL)。Intervene フェーズ(フェーズ2、`intervention.yaml` 保存時点)では `interventions.yaml` への書き込みを行ってはならない(SHALL NOT)。`rerun_turn`(`add-session-autonomy`、D112: 旧 artifact を `turn_NNNN_discarded_<n>` へ退避)によってあるターンが再実行された場合、破棄された attempt の event id / state diff id を参照している既存エントリは、`session-autonomy` の rerun 操作により `superseded_by_rerun: true` に更新される以外、内容を変更されてはならない(SHALL、上書き禁止の原則を維持する)。再実行後の Commit 完了時点で、新しい event id / state diff id を参照する新規エントリが追記されなければならない(SHALL)。commit-mode が `review` でありターンが `pending_review`/`stopped_for_review` のまま確定していない場合の扱いは、本 change の対象外とする(session-autonomy との調整事項)。

#### Scenario: 履歴インデックスが intervention をターンをまたいで累積する
- **WHEN** 複数ターンにわたって Intervention が確定する
- **THEN** `interventions.yaml` には全ターンの intervention エントリが蓄積され、既存エントリは上書きされない

#### Scenario: intervention から結果イベントを追跡できる
- **WHEN** `int_0042` の `world_directive` が `event_0081` を発生させた
- **THEN** `interventions.yaml` の `int_0042` エントリから `event_0081` への参照をたどれる

#### Scenario: rerun 後、破棄された attempt のエントリは superseded_by_rerun でマークされ新エントリが追記される
- **WHEN** あるターンが `rerun_turn` により再実行され、新しい event id / state diff id で Commit が完了する
- **THEN** 破棄された旧 attempt の event id / state diff id を参照する既存の `interventions.yaml` エントリは `superseded_by_rerun: true` に更新され、新しい event id / state diff id を参照する新規エントリが追記される

### Requirement: Interpreter の決定性
Intervention Interpreter は llm-provider の mock provider 契約(spec-foundation §8、`add-llm-provider` の Mock Provider 決定性要件)に従い、同一の `random_seed`・同一の自由文入力に対して常に同一の Intervention 群・confidence・interpretation summary を生成しなければならない(SHALL)。これにより Interpreter を含むテストがネットワークなしに決定的に実行できなければならない(SHALL)。

#### Scenario: mock provider による決定的な解釈結果の再現
- **WHEN** 同一の `random_seed` と同一の自由文入力で Interpreter を mock provider 経由で2回呼び出す
- **THEN** 2回の出力(Intervention 群・confidence・summary)は完全に一致する
