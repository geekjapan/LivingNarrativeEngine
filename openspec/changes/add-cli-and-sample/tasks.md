## 1. CLIスケルトンと`init`

- [ ] 1.1 `living_narrative.cli` パッケージと typer app のエントリポイントを作成し、`pyproject.toml` に `living-narrative` スクリプトを登録する
- [ ] 1.2 共通のエラーハンドリング(exit code 0/1/2 契約)と人間可読エラー出力のユーティリティを実装する
- [ ] 1.3 `minimal` テンプレート(project.yaml + 空のワークスペース一式)を実装する
- [ ] 1.4 `init` サブコマンド(`--title` `--genre` `--tone` `--template` `--output`)を実装する
- [ ] 1.5 未登録テンプレート名指定時の明示的エラーを実装する
- [ ] 1.6 `init` の pytest(mist_station/minimal 両テンプレートでの生成内容検証、未登録テンプレートのエラー検証)を書く

## 2. `turn` / `auto`

- [ ] 2.1 `turn` サブコマンド(`--project`)を実装し、engine API(turn-pipeline)を呼び出して `narration.md` 本文とステータス行を標準出力へ出力する
- [ ] 2.2 未解決ターンが残っている場合のブロックとエラー出力を実装する
- [ ] 2.3 `--intervention` フラグ(自由文 → Intervention Interpreter 経由)を実装する
- [ ] 2.4 `--type` + 構造化フラグ(直接入力パス)を実装し、`--intervention` との同時指定エラーを実装する
- [ ] 2.5 `--as <mode>` によるターン限定の `user_mode` 一時上書きを実装する(`--as player_character` は明示的エラーとする)
- [ ] 2.6 `auto` サブコマンド(`--project` `--turns N`)を実装し、session-autonomy の停止条件判定に従って進行・早期停止する
- [ ] 2.7 `auto --until scene_end` を実装し、`--turns` との同時指定エラーを実装する
- [ ] 2.8 `turn`/`auto` の pytest(標準出力内容、ブロック、介入反映、排他フラグエラー、早期停止、scene_end 停止)を書く

## 3. `review` / `status`

- [ ] 3.1 `review` サブコマンド(pending diff の人間可読提示)を実装する
- [ ] 3.2 `--decision accept|reject|rerun` の非対話フラグを実装する
- [ ] 3.3 `--decision partial --apply <index...>`(0始まりインデックスのカンマ区切り/繰り返し指定)の非対話フラグを実装する
- [ ] 3.4 `--decision edit --patch <file>` の非対話フラグを実装する
- [ ] 3.5 pending 対象が存在しない場合の正常終了(exit code 0)パスを実装する
- [ ] 3.6 TTY 無し・決定フラグ不足時の即時エラー終了(ブロッキング禁止)を実装する
- [ ] 3.7 `status` サブコマンド(人間可読出力)を実装する
- [ ] 3.8 `status --json` を実装する
- [ ] 3.9 `review`/`status` の pytest(各 decision フラグでの適用結果、pending 不在時の挙動、非対話エラー終了、JSON スキーマ検証)を書く

## 4. `export replay`

- [ ] 4.1 `living_narrative.export_replay` パッケージを作成し、turn artifact 読み込み(`meta.yaml`/`narration.md`/`intervention.yaml`/`rolls.yaml`/`events.yaml`/`state_diff.yaml`/`review.yaml`。`events.yaml` は reader 可視イベントの `Event.roll_ids` から reader 可視 roll を導出するために必須)を実装する
- [ ] 4.2 `novel` レンダラ(本文のみ連結)を実装する
- [ ] 4.3 `log` レンダラ(ターン見出し・intervention要約・roll要約・diff要約 + 本文)を実装する
- [ ] 4.4 `pending_review`/`stopped_for_review`/`failed` ターンのギャッププレースホルダ挿入を実装する
- [ ] 4.5 reader 可視性フィルタ(gm_vault/hidden_facts/secrets/private_mind を一切読み込まない)を実装する
- [ ] 4.6 出力先ディレクトリの自動作成と、applied ターンが1件も無い場合のエラー終了を実装する
- [ ] 4.7 `export replay` CLI サブコマンドを実装し、`--project` `--output` `--style` を配線する
- [ ] 4.8 export-replay の pytest(novel/log 出力内容、再実行時のバイト単位一致、ギャップ表記、可視性フィルタ、reader 可視イベントの `roll_ids` 経由の roll フィルタ(`gm_only` イベントのみが参照する roll が除外されること)、エラー終了)を書く

## 5. サンプル世界「霧の駅」

- [ ] 5.1 `world.yaml`(地下駅・霧・封印施設に関わる laws/parameters)を作成する
- [ ] 5.2 `canon.yaml`(確定事実)を作成する
- [ ] 5.3 4キャラクター(リナ・カイ・ミラ・追跡者)の `characters/*.yaml`(knowledge/secrets/private_mind/goals/emotions を含む)を作成する
- [ ] 5.4 `gm_vault.yaml`(隠し真実3件: 封印施設の存在・カイの部分的知識・ミラの正体)を作成し、design.md D3 に従って各真実を関連キャラクターの knowledge/secrets/private_mind に接続する
- [ ] 5.5 `relationships.yaml`(4キャラクター間の trust/affection/tension/suspicion 初期値)を作成する
- [ ] 5.6 `scene_001.yaml`(初期状況: リナとカイが地下駅で足音を聞く、reader_visible_facts/hidden_facts)を作成する
- [ ] 5.7 `reader_state.yaml`・`timeline.yaml`・`unresolved_threads.yaml` の初期空データを作成する
- [ ] 5.8 `mist_station` テンプレートとして `init` から生成できるよう配線する
- [ ] 5.9 サンプル世界データの pytest(スキーマ検証、隠し真実とキャラクターの関連付け検証)を書く

## 6. 20ターンスモークテスト

- [ ] 6.1 固定 `random_seed` + 決定的な mock provider 応答セットを20ターン分用意する
- [ ] 6.2 ターン3・6向けの構造化直接入力介入(design.md D4)をテストフィクスチャとして用意する
- [ ] 6.3 `tests/smoke/test_mist_station_20_turns.py` を作成し、20ターン完走(MVP成功条件の範囲上限)を検証する
- [ ] 6.4 ターン3・6の介入が翌ターンの narration/state に反映されることを検証する
- [ ] 6.5 roll が `rolls.yaml` に記録されることを検証する
- [ ] 6.6 state diff の保存・適用を検証する
- [ ] 6.7 20ターンを通じて error 級 leak 検出が発生しないことを検証する
- [ ] 6.8 5ターン目終了時点からの resume で6〜20ターン目が完走することを検証する
- [ ] 6.9 `export replay` により `replay.md` が生成され、隠し真実3件の文言が一切含まれないことを検証する

## 7. README・仕上げ

- [ ] 7.1 README にクイックスタート(`uv sync --extra dev` → `init` → `turn` → `auto` → `export replay`、Appendix D 準拠)を追記する
- [ ] 7.2 README にセキュリティ注意(`.env` での API キー管理、workspace は private 前提、ログに秘密情報を出さない)を追記する
- [ ] 7.3 `uv run pytest -q` で全テスト(cli/export_replay/smoke)がグリーンであることを確認する
- [ ] 7.4 `docs/spec-foundation.md`・`docs/project_plan.md`(企画書 §21.4)との整合を最終確認し、齟齬があれば報告する
