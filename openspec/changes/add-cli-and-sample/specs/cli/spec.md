# cli

`init` サブコマンドの完全な契約(`--genre`/`--tone`/`--template`/`--output`、テンプレートレジストリ、未登録テンプレート名のエラー処理を含む)は `project-workspace` capability の Requirement「init コマンドによるプロジェクト作成」(MODIFIED、`specs/project-workspace/spec.md` 参照)を正本とし、本 spec には重複定義しない。

## ADDED Requirements

### Requirement: `turn` による単一ターン実行と標準出力仕様
`living-narrative turn --project <path>` は、指定プロジェクトの次のターンを1回実行し、`narration.md` の本文を標準出力へ日本語で出力しなければならない(SHALL)。出力には、少なくともターン番号・ターンステータス(`applied`/`pending_review`/`stopped_for_review`/`failed`)を示すステータス行を含めなければならない(SHALL)。CLI 自体はターン実行のビジネスロジック(state diff 計算、可視性判定、乱数消費等)を実装せず、turn-pipeline capability の公開 API 呼び出し結果をそのまま出力に整形するのみでなければならない(SHALL)。

#### Scenario: 正常系での標準出力
- **WHEN** pending review の無いプロジェクトで `living-narrative turn --project projects/mist_station/project.yaml` を実行する
- **THEN** 標準出力に当該ターンの `narration.md` 本文とステータス行(ターン番号・`applied` 等)が日本語で出力され、exit code は 0 である

#### Scenario: 未解決ターンが存在する場合のブロック
- **WHEN** 直前のターンが `pending_review` のまま残っているプロジェクトで `living-narrative turn --project <path>` を実行する
- **THEN** CLI はターンを実行せず、`review` コマンドでの解決が必要である旨の人間可読エラーを出力して非ゼロの exit code で終了する

### Requirement: `turn` の自由文介入
`living-narrative turn --project <path> --intervention "<自由文>"` は、指定した自由文を Intervention Interpreter(`intervention` capability)へ渡し、解釈結果を当該ターンの Intervene フェーズへ適用しなければならない(SHALL)。

#### Scenario: 自由文介入の反映
- **WHEN** `living-narrative turn --project <path> --intervention "ここで停電を起こす。ただし原因はまだ明かさない"` を実行する
- **THEN** 当該ターンの `intervention.yaml` に、自由文から解釈された1件以上の Intervention が記録される

### Requirement: `turn` の構造化介入フラグと自由文との排他性
`living-narrative turn` は `--type <intervention-type>` と、それに付随する構造化フラグ(対象・内容・制約等)により、LLM interpreter を経由しない型付き直接入力介入を受け付けなければならない(SHALL)。`--intervention` と `--type` が同時に指定された場合、CLI はどちらか一方を無視して実行を継続してはならず、明示的なエラーで終了しなければならない(SHALL)。

#### Scenario: 構造化介入の直接入力
- **WHEN** `living-narrative turn --project <path> --type character_directive --target char_002 --content "物音に気づいて振り返る"` を実行する
- **THEN** LLM interpreter を経由せず、指定内容そのままの Intervention が `intervention.yaml` に記録される

#### Scenario: 自由文と構造化フラグの同時指定エラー
- **WHEN** `living-narrative turn --project <path> --intervention "何か起こす" --type character_directive --target char_002` を実行する
- **THEN** CLI はターンを実行せず、`--intervention` と `--type` は同時指定できない旨のエラーを出力して非ゼロの exit code で終了する

### Requirement: `turn` の `--as` によるモード一時上書き
`living-narrative turn --project <path> --as <user_mode>` は、当該ターンに限り `project.yaml` の `user_mode` を指定値へ一時的に上書きしなければならない(SHALL)。プロジェクトファイル自体の `user_mode` は変更してはならない(MUST NOT)。`--as` に `player_character` を指定した場合、CLI は上書きを実行せず明示的なエラーで終了しなければならない(SHALL): `player_character` モードはセッション開始時の `char_id` 紐付けを前提とし(session-autonomy 準拠)、単発ターンの一時上書きでは紐付け先を表現できないため。

#### Scenario: 一時的なGod Mode昇格
- **WHEN** `user_mode: assistant_gm` のプロジェクトで `living-narrative turn --project <path> --as god --type canon_edit ...` を実行する
- **THEN** 当該ターンは `god` の権限で intervention の permission 判定を通過し、実行後の `project.yaml` の `user_mode` は `assistant_gm` のまま変化しない

#### Scenario: `--as player_character` はエラーになる
- **WHEN** `living-narrative turn --project <path> --as player_character` を実行する
- **THEN** CLI はターンを実行せず、`player_character` への一時上書きはサポートされない旨のエラーを出力して非ゼロの exit code で終了する

### Requirement: `auto` による複数ターン自動進行
`living-narrative auto --project <path> --turns N` は、session-autonomy の停止条件判定に従って最大 N ターンを自律進行しなければならない(SHALL)。停止条件に該当した場合、指定ターン数に達する前でも進行を止め、標準出力に停止理由を示さなければならない(SHALL)。

#### Scenario: 指定ターン数までの正常進行
- **WHEN** 停止条件に該当しないサンプル世界で `living-narrative auto --project <path> --turns 5` を実行する
- **THEN** 5ターン分の `narration.md` が順に標準出力へ出力され、`workspace/runs/turn_0001` 〜 `turn_0005` が生成される

#### Scenario: 停止条件による早期停止
- **WHEN** 3ターン目で session-autonomy の停止条件(例: 重大な秘密の公開)に該当する状況で `living-narrative auto --project <path> --turns 10` を実行する
- **THEN** 進行は3ターン目で止まり、標準出力に停止理由と対応する turn ステータス(`stopped_for_review` 等)が示される

### Requirement: `auto --until scene_end` によるシーン終了までの進行
`living-narrative auto --project <path> --until scene_end` は、`--turns` の代わりに現在のシーンが終了するまで自律進行しなければならない(SHALL)。`--turns` と `--until` は同時指定を許可しない(SHALL NOT)。

#### Scenario: シーン終了までの進行
- **WHEN** シーンが3ターン後に終了する状況で `living-narrative auto --project <path> --until scene_end` を実行する
- **THEN** 進行はシーン終了と判定されたターンで止まり、それ以降のターンは実行されない

#### Scenario: --turnsとの同時指定エラー
- **WHEN** `living-narrative auto --project <path> --turns 5 --until scene_end` を実行する
- **THEN** CLI は進行を開始せず、`--turns` と `--until` は同時指定できない旨のエラーを出力して非ゼロの exit code で終了する

### Requirement: `review` による pending diff のインタラクティブフロー
`living-narrative review --project <path>` は、`pending_review` または `stopped_for_review` 状態の直近ターンの state diff を人間可読な形で提示し、accept(全適用)/reject(全却下・状態不変)/partial(部分適用)/edit(内容編集後に適用)/rerun(当該ターンを再実行)のいずれかをユーザーに選択させなければならない(SHALL)。全ての選択肢は、対話プロンプトに応じるだけでなく、対応する非対話フラグ(例: `--decision accept`、`--decision partial --apply <index> ...`、`--decision edit --patch <file>`、`--decision rerun`)でも指定できなければならない(SHALL)。`--apply` は session-autonomy の partial 適用契約(change のインデックス集合による選択)に合わせ、0始まりのインデックス値をカンマ区切りまたはフラグ繰り返しで受け取らなければならない(SHALL)。パスやその他のキーによる選択方式は提供しない(SHALL NOT)。

#### Scenario: accept全適用の非対話実行
- **WHEN** `living-narrative review --project <path> --decision accept` を実行する
- **THEN** 対象ターンの state diff が全件適用され、ターンステータスが `applied` になり、対話プロンプトは表示されない

#### Scenario: partial適用の非対話実行
- **WHEN** state diff が3件の change を含むターンで `living-narrative review --project <path> --decision partial --apply 0,2` を実行する
- **THEN** インデックス0と2の change のみが適用され、インデックス1は未適用のまま state diff に記録される

### Requirement: `review` の pending 不在時の挙動
`living-narrative review --project <path>` は、`pending_review`/`stopped_for_review` のターンが存在しない場合、レビュー対象が無い旨を標準出力に示して正常終了(exit code 0)しなければならない(SHALL)。エラーとして扱ってはならない(MUST NOT)。

#### Scenario: レビュー対象が無い場合
- **WHEN** 全ターンが `applied` 済みのプロジェクトで `living-narrative review --project <path>` を実行する
- **THEN** 「レビュー対象のターンはありません」旨のメッセージが出力され、exit code は 0 である

### Requirement: `status` の人間可読出力とJSON出力
`living-narrative status --project <path>` は、現在のターン番号、pending review の有無とターンステータス、現在の `user_mode`/`autonomy_level`、world state の要約(少なくとも現在シーンと主要 world parameters)を人間可読な形式で標準出力へ表示しなければならない(SHALL)。`--json` を指定した場合、同じ情報を機械可読な JSON として標準出力へ出力しなければならない(SHALL)。

#### Scenario: 人間可読なステータス表示
- **WHEN** `living-narrative status --project <path>` を実行する
- **THEN** 現在のターン番号・pending review の有無・`user_mode`・`autonomy_level`・現在シーンの要約が日本語で標準出力に表示される

#### Scenario: JSON形式でのステータス出力
- **WHEN** `living-narrative status --project <path> --json` を実行する
- **THEN** 標準出力は妥当な単一の JSON オブジェクトであり、少なくとも `current_turn`・`pending_review`・`user_mode`・`autonomy_level` のキーを含む

### Requirement: 非対話フラグの網羅性とexit code契約
`living-narrative` の全対話プロンプト(`review` の決定選択を含む)には、同等の結果を得られる非対話フラグが存在しなければならない(SHALL)。TTY が存在しない環境(CI等)で対話プロンプトが必要になった場合、CLI は無限にブロックしてはならず(MUST NOT)、必要なフラグが不足している旨のエラーで即座に終了しなければならない(SHALL)。exit code は、正常終了を `0`、実行時エラー(ターン失敗・provider エラー等)を `1`、引数/入力の検証エラー(未知のテンプレート名・不正なプロジェクトパス・排他フラグの同時指定等)を `2` としなければならない(SHALL)。

#### Scenario: 非対話環境でのプロンプト省略
- **WHEN** TTY の無い環境で、決定フラグを指定せずに `living-narrative review --project <path>` を実行する
- **THEN** CLI は対話入力を待たずに、決定フラグが不足している旨のエラーを出力して exit code `2` で終了する

#### Scenario: exit code契約の検証
- **WHEN** 存在しないプロジェクトパスを指定して `living-narrative status --project projects/does_not_exist/project.yaml` を実行する
- **THEN** exit code は `2` であり、標準エラー出力にプロジェクトが見つからない旨の人間可読メッセージが出力される

### Requirement: サンプル世界での20ターンスモークテスト
`mist_station` テンプレートと mock provider・固定 `random_seed` を用いた20ターンの smoke test は、企画書 §21.4 の MVP 成功条件(サンプル世界を10〜20ターン破綻せず進められる)のうち範囲の上限を回帰的に検証しなければならない(SHALL)。当該 smoke test は決定的でなければならず(SHALL)、少なくとも次のすべてを検証しなければならない(SHALL): (1) 20ターンが `failed` にならず完走すること、(2) ターン3・ターン6で与えた介入がそれぞれ翌ターンの narration/state に反映されること、(3) 各ターンで少なくとも1件以上の roll が `rolls.yaml` に記録されるターンが存在すること、(4) state diff が保存され、review or auto-apply を経て適用されること、(5) 20ターンを通じて error 級の情報リーク検出(leak checker)が発生しないこと、(6) 途中(例: 5ターン目)でプロセスを終了した状態から `resume` して残りのターンを完走できること、(7) `living-narrative export replay` で `replay.md` が生成され、`gm_vault` の隠し真実3件のいずれの文言も含まれないこと。

#### Scenario: 20ターン完走とMVP成功条件の一括検証
- **WHEN** 固定 seed・mock provider で `mist_station` テンプレートから生成したプロジェクトに対し、ターン3・6で介入を与えつつ `living-narrative auto --turns 20` 相当の処理を実行する
- **THEN** 上記(1)〜(7)のすべての検証項目が満たされることを pytest で確認できる

#### Scenario: 中断からのresume
- **WHEN** 5ターン完了時点でプロセスを終了させ、同一プロジェクトに対して再度ターン実行コマンドを呼び出す
- **THEN** ターン6から実行が再開され、6〜20ターン目が完走し、1〜5ターン目の artifact・state は変更されない
