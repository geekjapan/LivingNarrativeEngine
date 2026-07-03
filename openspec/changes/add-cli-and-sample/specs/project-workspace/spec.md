# project-workspace

## MODIFIED Requirements

### Requirement: init コマンドによるプロジェクト作成
`living-narrative init --title <str> [--genre <str>] [--tone <str>] [--template <name>] --output <dir>` コマンドは、必須オプション `--title` を受け取り、指定した `--output` ディレクトリにプロジェクトディレクトリと `project.yaml`、workspace 一式(spec-foundation §2/§5・企画書 Appendix B/C 準拠)を生成しなければならない(SHALL)。`--template` には `mist_station`(サンプル世界「霧の駅」)と `minimal`(空のたたき台)の2種を指定でき、省略時は `minimal` を既定として使用しなければならない(SHALL)。`minimal` テンプレートが生成する state ファイルの内容は、後続 change が本格的なテンプレートで置き換え可能な最小の空ワールド構成でよい。`mist_station` テンプレートは、世界「霧の駅」(舞台: 霧に包まれた旧市街の地下駅)、4キャラクター(リナ・カイ・ミラ・追跡者)、`gm_vault` に隠し真実3件(封印施設の存在・カイの部分的知識・ミラの正体)、`scene_001`(初期状況: リナとカイが地下駅で足音を聞く)を含まなければならない(SHALL)。未登録のテンプレート名を指定した場合、CLI は既定テンプレートへフォールバックせず、明示的なエラーメッセージと非ゼロの exit code で終了しなければならない(SHALL)。`--genre`/`--tone` を指定した場合、それぞれの値を `project.yaml` の `genre`/`tone` フィールドへそのまま設定しなければならない(SHALL)。`--title` 以外で明示的に指定されなかった `project.yaml` フィールドは次の固定既定値を用いなければならない(SHALL): `id` は `--title` から生成する ASCII 英数字とハイフンのみの slug(ASCII で表現できない場合は固定文字列 `"project"` にフォールバックする)、`genre`/`tone` は未指定時は空文字列、`autonomy_level` は `"manual"`、`user_mode` は `"assistant_gm"`(add-project-foundation と同じ既定。`watcher`+`manual` は session-autonomy の正規化対象のため用いない)、`random_seed` は実行のたびに一意な自動生成値、`renderer` は `"novel"`、`llm.provider` は `"mock"`、`llm.model` は `"mock-v1"`、`workspace.root`/`state`/`runs`/`exports` は企画書 Appendix B と同じ相対パス(`workspace`, `workspace/state`, `workspace/runs`, `workspace/exports`)。

#### Scenario: 新規プロジェクトの作成(テンプレート省略時)
- **WHEN** 存在しない出力先パスを指定して `living-narrative init --title "霧の駅"` を実行する
- **THEN** コマンドは成功し、`project.yaml` の `title` に `"霧の駅"` が設定され、`llm.provider` に `"mock"` が設定され、`--template` 省略により `minimal` テンプレートで workspace レイアウトが規定どおり生成される

#### Scenario: mist_stationテンプレートでのプロジェクト生成
- **WHEN** `living-narrative init --title "霧の駅" --genre mystery_fantasy --tone quiet_ominous --template mist_station --output projects/mist_station` を実行する
- **THEN** `projects/mist_station/project.yaml` と `workspace/state/characters/` 配下に4キャラクター分のファイル、`workspace/state/gm_vault.yaml` に隠し真実3件、`workspace/state/scenes/scene_001.yaml` が生成される

#### Scenario: 未登録テンプレート名でのエラー
- **WHEN** `living-narrative init --template unknown_template --output projects/foo` を実行する
- **THEN** CLI は既定テンプレートへフォールバックせず、テンプレートが存在しない旨の人間可読エラーを出力して非ゼロの exit code で終了する
