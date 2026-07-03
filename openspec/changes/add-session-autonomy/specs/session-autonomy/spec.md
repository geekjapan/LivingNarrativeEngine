## ADDED Requirements

### Requirement: ユーザーモードの権限マトリクス
Session Autonomy は企画書 §8 の6ユーザーモード(`watcher` `assistant_gm` `full_gm` `author` `player_character` `god`)それぞれについて、次の3属性からなる権限を定義しなければならない(SHALL): (1) 許可される介入タイプの集合(介入タイプの列挙とスキーマ自体は intervention capability が正本であり、本要件はモードごとにその集合の部分集合をバインドするのみ)、(2) 発行された state diff がレビューを要求するか否か、(3) `gm_vault.yaml` の内容が当該モードのユーザーに表示され得るか否か。マトリクスは以下のとおりでなければならない(SHALL):

| user_mode | 許可される介入タイプ(部分集合) | diff レビュー | gm_vault 表示 |
|---|---|---|---|
| `watcher` | なし(介入不可) | 対象外(ユーザー起因の介入がないため) | 不可 |
| `assistant_gm` | `scene_directive` `character_directive` `world_directive` `pacing_control` `tone_control` `reveal_control` `stop_condition` | 必須(停止条件到達時) | 可 |
| `full_gm` | `assistant_gm` の全て + `event_injection` `probability_bias` `hidden_truth_edit` `canon_edit` `dice_roll_request` `scene_pivot` `relationship_edit` `memory_edit` | 必須(autonomy level に従う頻度で) | 可 |
| `author` | `scene_directive` `tone_control` `pacing_control`(演出・文体・視点・伏線・感情線の指定用途に限定) | 必須 | 不可 |
| `player_character` | `character_directive`(本人の `char_id` 宛のみ) | 必須 | 不可 |
| `god` | 全介入タイプ + Canon/世界法則/秘密/パラメータ/乱数結果への直接編集 | レビュー自体をバイパスする(Requirement「God Mode の diff/ログ強制」を参照) | 可 |

本マトリクスは type→user_mode 許可関係の正本であり(SHALL、spec-foundation D114)、intervention capability の Interpreter が行う生成時チェック(D114 のいう「プラガブル判定」フック)へデータとして供給されなければならない(SHALL)。権限判定の実施点は当該生成時チェック一箇所のみであり、Session Autonomy は Interpreter が既に生成した intervention を受け取った後で本マトリクスを再評価し二重に却下する経路を持ってはならない(SHALL NOT)。モードに許可されていない介入タイプが要求された場合、Interpreter は本マトリクスの判定結果に基づいて生成そのものを拒否し、拒否理由を含むエラーを返さなければならない(SHALL、実施は intervention capability の責務、判定データは本 capability が供給する)。本マトリクスは intervention capability の Role Permission Hook(少なくとも `canon_edit`/`hidden_truth_edit` を `full_gm`/`god` のみへロックする)が持つ値と矛盾してはならない(SHALL、design.md D7)。

#### Scenario: watcher モードは介入を発行できない
- **WHEN** user_mode が `watcher` のプロジェクトで、ユーザーがいずれかの介入タイプを送信しようとする
- **THEN** Intervention Interpreter は session-autonomy の権限マトリクス(watcher は介入不可)に基づき生成時に介入を拒否し、watcher モードでは介入が許可されていないことを示すエラーを返す

#### Scenario: assistant_gm は許可外の介入タイプを拒否される
- **WHEN** user_mode が `assistant_gm` のプロジェクトで、`canon_edit`(assistant_gm には未許可)の介入が送信される
- **THEN** Intervention Interpreter は生成時に session-autonomy の権限マトリクスへ照会し、その介入を拒否する。拒否理由はモードの権限マトリクスに含まれないことである

#### Scenario: gm_vault はモードに応じて表示可否が決まる
- **WHEN** user_mode が `author` のセッションで、CLI が `gm_vault.yaml` の内容を表示しようとする
- **THEN** Session Autonomy は author モードでは gm_vault 表示不可であることを示し、表示要求を拒否する

### Requirement: Player Character モードの入力バインディング
`player_character` モードは、セッション開始時に単一の `char_id` に紐づかなければならない(SHALL)。当該モードでのユーザー入力は、Intervene フェーズにおいて自由文介入としてではなく、紐づいた `char_id` の行動候補として Act フェーズの出力(`agent_io/`)へ直接ルーティングされなければならない(SHALL)。このとき、当該キャラクターの Character Agent(LLM 呼び出し)はそのターンについてスキップされなければならない(SHALL)。他のキャラクターの Character Agent は通常どおり実行され、当該ターンの reader 可視情報の範囲で PC の行動に応答しなければならない(SHALL)。

#### Scenario: PC 入力がキャラクター行動として直接ルーティングされる
- **WHEN** user_mode が `player_character`(`char_id: char_002`)のターンで、ユーザーが行動テキストを入力する
- **THEN** そのテキストは `char_002` の行動候補として Act フェーズ出力に格納され、`char_002` の Character Agent は当該ターンで呼び出されない

#### Scenario: 紐づかないキャラクターへの character_directive は拒否される
- **WHEN** `char_id: char_002` に紐づく player_character モードで、`char_001` を対象とする `character_directive` が送信される
- **THEN** Intervention Interpreter は生成時に session-autonomy の char_id バインディング判定へ照会し、その介入を拒否する

### Requirement: 自律性レベルの意味論
Session Autonomy は企画書 §9 の5自律性レベル(`manual` `assist` `auto` `watch` `god`)を次のとおり定義しなければならない(SHALL): `manual` は毎ターンの Commit 前に必ずレビューゲートで停止する。`assist` は通常ターンを自律実行するが、有効化された停止条件のいずれかに合致した場合に停止する。`auto` は指定ターン数到達またはシーン終了、あるいは有効化された停止条件のいずれかに合致するまで自律実行する。`watch` は`checker_error`・`scene_end`・`target_turn_count_reached`・`stop_condition` を除く停止条件による停止を行わず、停止条件の発生は提示可能な「候補」としてログされるのみで、既定では提示自体もオフである。`god` は`checker_error`・`scene_end`・`target_turn_count_reached`・`stop_condition` を除く停止条件による停止を行わないが、発生した停止条件は必ずログに記録される。`stop_condition`(ユーザーが明示的に発行した停止要求)は `watch`/`god` を含む全レベルで必ず停止する(spec-foundation D119)。

#### Scenario: manual は毎ターン停止する
- **WHEN** autonomy_level が `manual` のセッションで1ターンを実行する
- **THEN** Commit フェーズの前でレビューゲートが提示され、ユーザーの決定なしに次のターンへ進まない

#### Scenario: watch は stop_condition 以外の停止条件で停止しない
- **WHEN** autonomy_level が `watch` のセッションで、有効化された「キャラクター死亡」停止条件に合致するターンを実行する
- **THEN** ターンは停止せず自律進行を継続し、当該条件の発生はログに記録される

### Requirement: Mode × Level の矛盾検出と正規化
Session Autonomy は user_mode と autonomy_level の組み合わせを検証し、次の矛盾する組み合わせを検出した場合、指定された値へ正規化した上で警告を発しなければならない(SHALL): (1) `watcher` モードと `manual` または `god` レベルの組み合わせは `watch` レベルへ正規化する(watcher は介入権限を持たないため、毎ターン確認の強制も全ガードレール解除も意味を持たない)。(2) `player_character` モードと `auto` `watch` `god` のいずれかのレベルの組み合わせは `assist` レベルへ正規化する(player_character はターンごとに本人の入力を必要とするため、ユーザー入力を待たずに進行するレベルとは両立しない)。上記以外の組み合わせは全て有効であり、正規化を行わない(SHALL NOT)。

#### Scenario: watcher + manual は watch へ正規化される
- **WHEN** user_mode `watcher` と autonomy_level `manual` の組み合わせでセッションを開始する
- **THEN** autonomy_level は `watch` へ正規化され、正規化が行われたことを示す警告がログに記録される

#### Scenario: player_character + auto は assist へ正規化される
- **WHEN** user_mode `player_character` と autonomy_level `auto` の組み合わせでセッションを開始する
- **THEN** autonomy_level は `assist` へ正規化され、警告がログに記録される

#### Scenario: 有効な組み合わせは正規化されない
- **WHEN** user_mode `assistant_gm` と autonomy_level `assist` の組み合わせでセッションを開始する
- **THEN** 正規化は行われず、指定どおりの組み合わせでセッションが開始される

### Requirement: 停止条件の判定とレベル別適用
Session Autonomy は企画書 §10.6 に定める10件の停止条件を判定しなければならない(SHALL): `character_death`(キャラクター状態が死亡へ遷移)、`major_canon_change`(重大度の高い canon.yaml 変更)、`relationship_threshold_crossing`(relationships.yaml の値が設定閾値を跨ぐ)、`major_secret_reveal`(gm_vault または secrets の可視性が reader へ昇格)、`checker_error`(consistency-checks capability が error 級の finding を報告)、`leak_suspicion`(leak checker が warn 以上の finding を報告)、`heavy_roll_failure`(Conflict Resolver が重大失敗として roll をフラグする)、`scene_end`(現在シーンが終了)、`target_turn_count_reached`(auto ループの目標ターン数に到達)、`stop_condition`(ユーザーが発行した `stop_condition` 介入が当該ターンで確定した。spec-foundation D119)。各条件の適用有無は autonomy level ごとに次のとおりでなければならない(SHALL): `assist` と `auto` は10条件全て(有効化されているもの)で停止する。`watch` と `god` は `checker_error`・`scene_end`・`target_turn_count_reached`・`stop_condition` の4条件でのみ停止し、残る6条件(`character_death` `major_canon_change` `relationship_threshold_crossing` `major_secret_reveal` `leak_suspicion` `heavy_roll_failure`)は停止せずログにのみ記録する。`stop_condition` はユーザーが明示的に発行した停止要求であるため、`watch`/`god` を含む全 autonomy level で無条件に停止しなければならない(SHALL、spec-foundation D119、Requirement「停止条件のプロジェクト設定」による無効化の対象外)。`manual` は毎ターン停止するため停止条件の適用有無に依存しない。

#### Scenario: assist はキャラクター死亡で停止する
- **WHEN** autonomy_level `assist` のターン実行中に `character_death` 条件(有効化済み)に合致する
- **THEN** 自律進行はそのターンで停止し、レビューゲートが提示される

#### Scenario: god は checker_error では停止する
- **WHEN** autonomy_level `god` のターン実行中に consistency-checks が error 級の finding を報告する
- **THEN** god レベルであっても自律進行は停止し、finding がユーザーに提示される

#### Scenario: god は重大秘密の開示では停止しない
- **WHEN** autonomy_level `god` のターン実行中に `major_secret_reveal` 条件に合致する
- **THEN** 自律進行は停止せず継続し、当該条件の発生がログに記録される

#### Scenario: watch は stop_condition では停止する
- **WHEN** autonomy_level `watch` のターン実行中に、ユーザーが発行した `stop_condition` 介入が当該ターンで確定する
- **THEN** watch レベルであっても自律進行は停止し、レビューゲートが提示される

#### Scenario: god は stop_condition では停止する
- **WHEN** autonomy_level `god` のターン実行中に、ユーザーが発行した `stop_condition` 介入が当該ターンで確定する
- **THEN** god レベルであっても自律進行は停止し、レビューゲートが提示される

### Requirement: 停止条件のプロジェクト設定
Session Autonomy は、`stop_condition` を除く9つの停止条件を `project.yaml` 単位で有効/無効を切り替え可能にし、`relationship_threshold_crossing` のような閾値を持つ条件については閾値をプロジェクト設定として指定可能にしなければならない(SHALL)。この設定は `project.yaml` のトップレベル任意フィールド `stop_conditions`(条件名をキー、`enabled`(bool、既定 `true`)と任意の `threshold`(整数)を値とする辞書。スキーマ定義とロード時検証は本 change の MODIFIED Requirement「project.yaml スキーマ」(`specs/project-workspace/spec.md`)を正本とする)から読み取らなければならない(SHALL)。設定が存在しない条件については、企画書 §10.6 に基づく既定値(全条件有効、閾値は関係性次元ごとに ±20 の変動)を用いなければならない(SHALL)。`stop_condition` はユーザーが能動的に発行した停止要求であり、プロジェクト設定による無効化の対象としてはならない(SHALL NOT、spec-foundation D119)。

#### Scenario: 無効化された停止条件は判定されない
- **WHEN** プロジェクト設定で `heavy_roll_failure` が無効化されている状態で、重大失敗ロールが発生する
- **THEN** 当該ターンは `heavy_roll_failure` を理由に停止しない

#### Scenario: 閾値未設定時は既定値が使われる
- **WHEN** プロジェクト設定に `relationship_threshold_crossing` の閾値指定がない状態で、trust が20以上変動する
- **THEN** 既定閾値(±20)に基づき停止条件の合致判定が行われる

### Requirement: GM レビューゲートのフロー
diff レビューを要求する user_mode(Requirement「ユーザーモードの権限マトリクス」参照)、または停止条件により停止したターンでは、Session Autonomy は生成された state diff を pending 状態として保持し、次の決定のいずれかを受け付けなければならない(SHALL): `accept_all`(全 change を適用)、`reject_all`(適用せず状態不変のまま次ターンへ、または再入力待ち)、`partial`(change のインデックス集合を選択して適用、残りは破棄)、`edit`(diff ファイルをユーザーが編集し、システムが state diff スキーマ(spec-foundation §5.1)で再検証してから適用)、`rerun_turn`(当該ターンの artifact を破棄し、ターン開始前の状態から再実行する。Requirement「Rerun の乱数消費セマンティクス」参照)。決定内容(選択肢・対象インデックス・編集差分・タイムスタンプ)は当該ターンの `review.yaml` に記録されなければならない(SHALL)。`partial`/`edit` の実行はターンパイプラインのフェーズ実行を経由せず、本 capability が state-model の diff 適用 API と add-turn-pipeline が公開する事後操作向けユーティリティを直接呼び出すことで完結させなければならない(SHALL、design.md D8)。`rerun_turn` についてパイプライン外で行うのは既存 attempt の退避(`turn_NNNN_discarded_<n>` へのリネーム)と `review.yaml` への決定記録のみであり(SHALL)、新しい attempt の実行自体は通常どおり TurnPipeline の8フェーズ全体(Load〜Commit)を経由して events・narration・checks・state diff を再生成しなければならない(SHALL)。

各決定は、spec-foundation §3 のターンステータス enum(`applied` | `pending_review` | `stopped_for_review` | `failed`)へ次のとおり写像されなければならない(SHALL、add-turn-pipeline の「次ターン番号の決定と未解決ターンによるブロック」— 解決は `applied` または `failed` のいずれかで確定する— と整合させるため): `accept_all`・`partial`・検証に成功した `edit` はターンステータスを `applied` にする。検証に成功した `edit` を適用する際は、編集前の `state_diff.yaml` を同一ターンディレクトリ内に `state_diff_pre_edit.yaml` として退避した上で(SHALL、監査可能性。D112 と同精神で削除・上書きしない)、`state_diff.yaml` を編集後の diff 内容で置き換えて保存し(SHALL、原子的書き込み)、保存される inverse diff(state-model の `InverseStateDiff`、`inverse_diff.yaml`)は編集後 diff の適用時に生成されたものでなければならない(SHALL)。これにより、ターン artifact(`state_diff.yaml`/`inverse_diff.yaml`)と実際に適用された状態変化が常に一致し、将来の rollback が編集後 diff の逆操作として正しく機能する。`reject_all` は、適用される change を空集合として扱った上でターンステータスを `applied` にする(状態への実変更はゼロだが、当該ターンは解決済みとして次ターンへ進行可能になる)。`rerun_turn` は当該ターンの attempt を `turn_NNNN_discarded_<attempt連番>` へリネームして保持し(design.md D6)、同一ターン番号 `turn_NNNN` で新しい attempt を実行するため、破棄された attempt 自体のステータス確定は不要である。

`review.yaml` は少なくとも次のフィールドを持たなければならない(SHALL): `turn`(対象ターン番号)、`decision`(`accept_all` | `reject_all` | `partial` | `edit` | `rerun_turn`)、`decided_at`(ISO 8601 タイムスタンプ)、`decided_by`(決定時の `user_mode`)、`applied_change_indices`(`partial` 時に適用されたインデックス集合。`accept_all`/`reject_all`/`edit` では省略可能)、`edit_diff`(`edit` 時の編集後 diff 内容。他の決定では省略)、`resulting_turn_status`(上記写像の結果)、`auto_applied`(god mode によるレビューバイパス経由の自動適用かどうかの真偽値。Requirement「God Mode の diff/ログ強制」参照)。`decision` が `reject_all` であることは、export-replay capability が読者向け正史から当該ターンの narration を除外するかどうかを判定する唯一の判定材料である(SHALL、spec-foundation D120)。当該ターンの `narration.md` 等の artifact 自体は削除・改変せず保持する。除外処理そのもの(export 実行時のフィルタリング)は export-replay capability の責務であり、本 capability の責務ではない。

#### Scenario: partial 適用は選択した change のみを反映する
- **WHEN** state diff が3件の change を含み、ユーザーが `partial` でインデックス [0, 2] を選択する
- **THEN** インデックス0と2の change のみが適用され、インデックス1は破棄される。`review.yaml` には選択内容が記録され、ターンステータスは `applied` になる

#### Scenario: edit は再検証を経てから適用される
- **WHEN** ユーザーが pending diff ファイルを編集して `edit` を選択する
- **THEN** システムは編集後の内容を state diff スキーマで再検証し、検証に通過した場合のみ適用してターンステータスを `applied` にする。適用後、編集前の diff は `state_diff_pre_edit.yaml` として退避され、`state_diff.yaml` は編集後の内容に、`inverse_diff.yaml` は編集後 diff から生成された逆操作になっている

#### Scenario: edit の検証失敗時は pending review が維持される
- **WHEN** ユーザーが編集した diff ファイルの内容が state diff スキーマの検証に失敗する
- **THEN** 適用は行われずエラーが提示される。ターンの pending review 状態(`pending_review` または `stopped_for_review`)は維持され、ユーザーは再度 `edit` を試みるか、他の決定(`accept_all`・`reject_all`・`partial`・`rerun_turn`)を選択できる

#### Scenario: reject_all は状態を変更せずターンを解決する
- **WHEN** ユーザーが `reject_all` を選択する
- **THEN** state diff は適用されず、状態ファイルはターン実行前と同一のまま維持される。`review.yaml` に reject が記録され、ターンステータスは変更ゼロ件の `applied` として確定し、次ターンの実行が可能になる

#### Scenario: reject_all の記録は export-replay の除外判定に使われる
- **WHEN** `reject_all` が選択され `review.yaml` の `decision` に `reject_all` として記録される
- **THEN** 当該ターンの `narration.md` を含む artifact は削除されず保持されるが、export-replay capability はこの `decision` フィールドを参照して当該ターンの narration を読者向け正史から除外する(除外処理自体は export-replay capability が実装する)

### Requirement: Rerun の乱数消費セマンティクス
`rerun_turn` を実行する場合、Session Autonomy は既定でターン開始前の状態から新しい乱数シーケンス位置で再実行しなければならない(SHALL、既存の消費済み roll シーケンスは巻き戻さない)。ユーザーが同一シード再現を明示的に指定した場合(例: `--replay-same-seed`)に限り、当該ターン開始前の乱数消費数まで巻き戻してから再実行しなければならない(SHALL)。破棄された旧ターンの artifact は削除せず、`turn_NNNN_discarded_<attempt連番>`(spec-foundation §6 D112、design.md D6。add-turn-pipeline の failed ターン再試行と共有する命名契約)へリネームした上で監査可能な形で保持しなければならない(SHALL)。当該ターン番号より前の「乱数消費数」を算出する際(既定 rerun の続き位置・`--replay-same-seed` の巻き戻し先のいずれも)、対象ターンより前の全ターンについて、現存する `turn_NNNN` と当該ターン番号に対して破棄された全ての `turn_NNNN_discarded_*` の rng 消費数を合算しなければならない(SHALL、design.md D6)。破棄対象ターンに属する `interventions.yaml`(add-intervention 定義)の該当エントリには `superseded_by_rerun: true` を付与しなければならない(SHALL、design.md D6)。当該エントリは削除・上書きせず、`superseded_by_rerun` は監査マーカーとしてのみ機能する。

#### Scenario: 既定の rerun は新しい乱数列を消費する
- **WHEN** ターン18を `rerun_turn`(オプション指定なし)で再実行する
- **THEN** 再実行は元のターン18が消費した roll シーケンス位置の続きから新しい draw を行い、元のターン18の roll 結果とは独立した結果になり得る。破棄された元のターン18 artifact は `turn_0018_discarded_1` として保持され、当該 attempt に属する `interventions.yaml` エントリには `superseded_by_rerun: true` が付与される

#### Scenario: 同一シード再現指定時は同じ乱数列から再実行する
- **WHEN** ターン18を `rerun_turn --replay-same-seed` で再実行する
- **THEN** 乱数消費数はターン18開始前の値(ターン1〜17の `turn_NNNN` および同区間の `turn_NNNN_discarded_*` 全ての rng 消費数の合算)まで巻き戻され、元のターン18と同じ乱数消費位置から再実行される

#### Scenario: 再度 rerun された場合は attempt 連番が増える
- **WHEN** 一度 `rerun_turn` 済みのターン18(`turn_0018_discarded_1` を保持)に対し、さらに `rerun_turn` を実行する
- **THEN** 現存する `turn_0018` は `turn_0018_discarded_2` へリネームされ、新しい `turn_0018` attempt が実行される

### Requirement: セッション再開(resume)
Session Autonomy は、ワークスペースのファイル(turn artifact 群、`project.yaml`、状態ファイル)のみから次を復元できなければならない(SHALL): 最後に Commit が適用されたターン番号(`turn_NNNN` ディレクトリのみを対象とし、`turn_NNNN_discarded_*` は対象外とする。design.md D6)、pending 状態の review が存在するか否か、現在の user_mode と autonomy_level、乱数エンジンの消費済み draw 数(現存する各 `turn_NNNN/meta.yaml` に加え、全ての `turn_NNNN_discarded_*/meta.yaml` を含めた rng 消費数の累積。design.md D6、Requirement「Rerun の乱数消費セマンティクス」)。resume 実行時、pending review が存在する場合は、他のいかなる操作(次ターン実行、auto ループ開始等)よりも先にその review を提示しなければならない(SHALL、pending-review-first ルール)。

#### Scenario: pending review がある場合は resume 時に最優先で提示される
- **WHEN** ターン18に pending 状態の review が存在するワークスペースで `resume` を実行する
- **THEN** システムはターン19以降の実行を開始せず、まずターン18の pending review をユーザーに提示する

#### Scenario: resume は乱数消費数を正しく継続する
- **WHEN** これまでのターンで合計42回 draw したワークスペースで `resume` した後、1回追加で draw する
- **THEN** その draw は43回目として実行され、中断せず継続実行した場合と同じ結果になる

#### Scenario: resume は破棄された rerun attempt の乱数消費も累積に含める
- **WHEN** ターン18が1回 `rerun_turn`(既定、新規シーケンス消費)されており、破棄された `turn_0018_discarded_1` が K1 回、現存する `turn_0018` が K2 回 draw しているワークスペースで `resume` する
- **THEN** 乱数エンジンの消費済み draw 数にはターン1〜17の消費数に加え K1+K2 が含まれ、以降の draw は中断せず継続実行した場合と同じ結果になる

#### Scenario: pending review がない場合は最終ターンから継続する
- **WHEN** pending review が存在せず、最後に Commit されたターンが17であるワークスペースで `resume` する
- **THEN** システムはターン18から実行を継続する

### Requirement: Auto N ターンループ
Session Autonomy は、指定ターン数(N)または停止条件(有効化されている `scene_end` を含む)に到達するまでターンを連続実行するループを提供しなければならない(SHALL)。ループ中の各ターンは、通常のターン実行と同一の artifact 契約・レビュー契約に従わなければならない(SHALL)。ループはいつでも中断可能であり、中断時点までに Commit 済みのターンの状態は保持され、実行中だったターンの artifact は partial artifact として保存され、次回実行時に破棄または再実行の対象として扱われなければならない(SHALL、中断安全性)。

#### Scenario: N ターン到達でループが終了する
- **WHEN** `target_turn_count_reached` が N=5 で有効なループを、停止条件に合致しないまま実行する
- **THEN** ループは5ターン実行した時点で終了し、レビューゲートまたは完了通知が提示される

#### Scenario: 中断してもコミット済み状態は保持される
- **WHEN** auto ループの3ターン目実行中に処理が中断される
- **THEN** ターン1・2は Commit 済みとして状態に反映されたまま保持され、ターン3の artifact は partial artifact として保存され、状態には未適用のまま残る

### Requirement: God Mode の diff/ログ強制
`god` モードでの編集(Canon編集、世界法則編集、キャラクター秘密の変更、パラメータ直接変更、乱数結果の上書き等)は、レビューゲートによる accept/reject の対象とはならず自動適用されるが、いかなる場合も spec-foundation D107 に従い state diff として発行され、当該ターンの artifact に記録されなければならない(SHALL)。God Mode の編集について、diff の発行とログ記録を省略する経路があってはならない(SHALL NOT)。

#### Scenario: god モードの直接編集も diff として記録される
- **WHEN** user_mode `god` のユーザーが Canon を直接編集する
- **THEN** その変更は `state_diff.yaml` に change として記録され、レビューゲートの提示なしに適用される。`review.yaml` には god mode による自動適用であることが記録される
