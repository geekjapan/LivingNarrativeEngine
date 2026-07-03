# Proposal: add-cli-and-sample

## Why

`add-project-foundation` から `add-session-autonomy` までの各 change は、状態モデル・乱数・LLM provider・ターンパイプライン・agent・intervention・自律進行の判断ロジックを提供したが、それらを人間が実際に叩けるコマンドはまだ存在しない。また、企画書 §21 の MVP 成功条件(サンプル世界を10〜20ターン破綻せず進められる)を検証する具体的な世界データと回帰テストも無い。本 change は、これまでの全 capability を `living-narrative` CLI として束ね、サンプル世界「霧の駅」と20ターン smoke test で MVP 成功条件(10〜20ターンという範囲の上限)を実証し、第1バッチ(MVP)を完成させる。

## What Changes

- typer ベースの `living-narrative` エントリポイントを追加し、企画書 §29 のユーザーフロー(`init` / `turn` / `auto` / `review` / `status` / `export replay`)をサブコマンドとして実装する。第1バッチでは `web` コマンドは追加しない(spec-foundation D101)。
- `init` コマンドを追加する: `--title` `--genre` `--tone` `--template` `--output` を受け取り、Appendix B/C 準拠の `project.yaml` とワークスペース一式を生成する。テンプレートは `mist_station`(サンプル世界)と `minimal`(空のたたき台)の2種を提供する。
- `turn` コマンドを追加する: `--project` で指定したプロジェクトの1ターンを実行し、ナレーションを標準出力へ日本語で出力する。`--intervention "自由文"` で自由文介入を、`--type <intervention-type> ...` の構造化フラグで型付き直接入力介入を受け付ける(両者は排他)。`--as <mode>` でそのターンに限り `user_mode` を一時的に上書きする。
- `auto` コマンドを追加する: `--project` `--turns N` で指定ターン数を自律進行し、`--until scene_end` でシーン終了までの進行を選べる(session-autonomy の停止条件判定に委譲)。
- `review` コマンドを追加する: pending な state diff を提示し、accept / reject / partial / edit / rerun のインタラクティブフローを提供する。全プロンプトに対応する非対話フラグを用意し、CI/スクリプトから完全に非対話実行できるようにする。
- `status` コマンドを追加する: 現在のターン番号、pending review の有無、`user_mode`/`autonomy_level`、world state の要約を表示する。`--json` で機械可読な出力に切り替えられる。
- `export replay` コマンドを追加し、`export-replay` capability(下記)を呼び出す。
- CLI は engine 層の公開 API を呼び出す薄いレイヤーとして実装し、状態遷移・diff 計算・可視性判定等のビジネスロジックを CLI モジュール内に実装しない。
- `export-replay` capability を追加する: turn artifact(`narration.md` / `intervention.yaml` / `rolls.yaml` / `state_diff.yaml` 等)から `replay.md` を決定的に(LLM 呼び出し無しで)組み立てる。`novel`(本文のみ)と `log`(ターン見出し・介入・ロール・適用diff要約を注釈として含む)の2スタイルを提供し、reader 可視性(spec-foundation §4)を厳守して `gm_vault`・hidden 情報を一切含めない。失敗/停止ターンはリプレイ上に欠落として明示する。
- サンプル世界「霧の駅」を `mist_station` テンプレートとして追加する(企画書 §21.5 準拠、拡張): world/canon/gm_vault(隠し真実3件: 封印施設の存在・カイの部分的知識・ミラの正体)/4キャラクター(リナ・カイ・ミラ・追跡者、それぞれ knowledge/secrets/private_mind を持つ)/relationships/`scene_001`。各隠し真実は、少なくとも1体のキャラクターが部分的に知る・関与することで、consistency-checks の leak checker が実際に検出対象を持つように設計する。
- 20ターン smoke test を追加する(企画書 §21.4 の MVP 成功条件をそのまま回帰テスト化し、10〜20ターンという範囲の上限を実証する): mock provider・固定 seed で決定的に実行し、(1) 20ターン完走、(2) ターン3・6の介入が翌ターンに反映される、(3) roll がログされる、(4) diff が保存・適用される、(5) error 級の leak 検出が無い、(6) 中断からの resume が成功する、(7) `replay.md` が生成され隠し真実を含まない、をすべて検証する。
- README にクイックスタート(`uv sync` → `init` → `turn` → `auto` → `export replay`)とセキュリティ注意(`.env` での API キー管理、workspace は private 前提であること)を追記する。

## Capabilities

### New Capabilities

- `cli`: `living-narrative` の各サブコマンド(`init`/`turn`/`auto`/`review`/`status`/`export`)、非対話フラグ、標準出力・エラー・exit code 契約、サンプル世界テンプレートの内容契約、20ターン smoke test を提供する。
- `export-replay`: turn artifact から `replay.md` を組み立てる決定的な export 処理(novel/log スタイル、可視性遵守、ギャップ処理)を提供する。

### Modified Capabilities

- `project-workspace`(init コマンドの完全版契約への置換): `add-project-foundation` が定義した最小の `init` コマンド契約(`--title` のみ)を、`--genre`/`--tone`/`--template`/`--output` フラグ・テンプレートレジストリ(`mist_station`/`minimal`)・未登録テンプレート名のエラー処理を含む完全版契約へ置換する。既存ディレクトリへの上書き拒否の契約は変更しない。

## Non-Goals

- `web` コマンド・Web UI(spec-foundation D101、第2バッチ以降)。
- TUI(curses等によるフルスクリーン対話画面)。
- シェル補完(bash/zsh/fish completion)の作り込み。
- 小説原案・章立て export、TRPGリプレイ export(企画書 §23.4、Phase 6)。`export replay` は novel/log の2スタイルのみを提供する。
- `mist_station` / `minimal` 以外のテンプレート追加。
- Web UI からの介入入力(intervention capability の非ゴールと同じ理由: spec-foundation D101)。

## Dependencies

- `add-session-autonomy`(`turn --as` のモード一時上書き、`auto --until`、`review` の accept/reject/partial/edit/rerun フロー、停止条件判定はすべて session-autonomy の意思決定ロジックに委譲する)。
- `add-project-foundation`(`project-workspace` capability の `init` Requirement を MODIFIED delta で完全版契約へ置換する)。
- 推移的に `add-state-model`(`status` の world state 要約、diff 表示、Event.roll_ids)、`add-random-engine`(roll ログの smoke test 検証)、`add-llm-provider`(mock provider による決定的実行)、`add-turn-pipeline`・`narration`(`turn`/`auto` が呼び出す実行基盤、`narration.md` を export-replay が読み込む、meta.yaml の status フィールド)、`add-agent-runtime`(consistency-checks の leak checker による smoke test の error 級検証)、`add-intervention`(`turn --intervention` / `--type` フラグ)にも依存する。

## Impact

- 新規: `src/living_narrative/cli/`(typer app・各サブコマンド)、`src/living_narrative/export_replay/`(replay 組み立てロジック・novel/log レンダラ)、`src/living_narrative/templates/mist_station/`・`src/living_narrative/templates/minimal/`(init テンプレート)、`tests/cli/`、`tests/export_replay/`、`tests/smoke/test_mist_station_20_turns.py`。
- 変更: `README.md`(クイックスタート・セキュリティ注意の追記)、`pyproject.toml`(`living-narrative` エントリポイント登録)。
- 本 change の完了をもって企画書 §21.4 の MVP 成功条件・§26.1 の MVP完成条件を満たす(第1バッチ完了)。
