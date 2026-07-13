---
id: 038
title: TRPGセッションモードとE7品質ゲート
status: done
created: 2026-07-11
---

# 038: TRPGセッションモードとE7品質ゲート

## 背景

E7で追加したPC参加、能力判定、構造化inventory、quest、encounter、簡易戦闘は個別には検証済みだが、同一セッションで相互に干渉せず動くことと、長尺退行を定量検知できることはまだ固定されていない。Issue 019の50ターンregression網をgame系へ拡張し、GM向けTRPGリプレイにもゲーム進行を監査できる情報を織り込んで、E7完了の品質ゲートとする。

## 設計

戦闘のResolve側（payload検証、roll/event生成、HPのStateDiff化）はIssue 037で実装済みである。Issue 038は通し品質ゲートに加え、Character Agentが有効な場面内対象へ`effects.combat`を生成するproducer prompt契約を追加する。

1. `player_character`モードのmock統合テストで数ターンを実行し、PC行動、`dice_roll_request`、inventory use、quest open/advance/resolve、encounter、combatをそれぞれ最低1回発火させる。全state変更は既存`StateDiff`経路を通し、roll/event/interventionの関連付けと情報スコープも確認する。
2. GM向け`export_replay/trpg.py`へcombatのattacker/defender/stakes/result、quest遷移、PC入力、encounter発火の注記を追加する。既存のroll・介入表示とGM注記スタイルを維持し、通常のreader向けexport契約は変えない。
3. `session/metrics.py`とmetrics CLIへgameメトリクスを追加する。combat発生数、questのopen/advance/resolve数、PC行動反映数、encounter発火数、skill checkの成功数・総数・成功率を、applied turnと既存artifactの正本から集計する。
4. Issue 019のmock 50ターン定点でgameメトリクスをassertし、長尺退行を検知する。テスト用の誘発はmock出力・sandbox状態に限定し、テンプレート正本を改変しない。
5. `sandbox/`にmist_stationまたはorbital_echoを初期化し、OmniRoute `auto/best-coding`でplayer_characterモード8〜12ターンを実行する。PC入力がResolveで調停され、combatとquestが各1回以上動いた証跡と数値をこのissueへ記録する。

## E7ゲート判定

mock統合テスト、gameメトリクス付き50ターンbench、実LLMスモークがすべてgreenであることをE7ゲート通過条件とする。一つでも未達なら`status: done`へ変更しない。

933件の全テスト、50ターンbench、実LLM 8ターンスモークがすべてgreenとなったため、**E7ゲート通過**と判定する。

## 検証記録

2026-07-11に以下を実行し、E7ゲート通過を確認した。実LLMではquest resolveが未発火だったが、
これは品質改善としてIssue 057が所管する検証負債であり、本IssueのE7ゲート判定を覆さない。

- mock統合: `NO_COLOR=1 uv run pytest tests/pipeline/test_trpg_session_e7.py -q` → `1 passed`。3ターン同一セッションでPC行動3、combat 1、quest open/advance/resolve各1、encounter 3、skill check成功1/総数1（成功率1.0）を確認した。
- 50ターンbench: `NO_COLOR=1 uv run pytest tests/smoke/test_mist_station_50_turns.py -q` → `1 passed in 10.73s`（60秒未満）。combat 1、quest open/advance/resolve各1、PC行動50、encounter 50、skill check成功1/総数1（成功率1.0）の決定値をassertした。
- 実LLMスモーク: `uv run living-narrative init --title 'Issue 038 E7実LLMスモーク' --output sandbox/issue038_llm --template mist_station`。gitignored sandboxだけで`user_mode: player_character`、`OPENAI_BASE_URL=http://127.0.0.1:20128/v1`、非空の`OPENAI_API_KEY`、OmniRoute `auto/best-coding`を設定し、`uv run living-narrative turn --project sandbox/issue038_llm/project.yaml --pc-action '<各ターンのPC行動>'`（停止時は`uv run living-narrative review --project sandbox/issue038_llm/project.yaml --decision accept_all`）を実行した。
- 実LLM数値: `uv run living-narrative status --project sandbox/issue038_llm/project.yaml`と`uv run living-narrative metrics --project sandbox/issue038_llm/project.yaml --json`で、turn 8、status内訳`applied: 8`、combat 7、quest open 0 / advance 1 / resolve 0、applied PC action 6、encounter 8、skill check成功0 / 総数0 / 成功率nullを確認した。PC入力はturn 1, 2, 4, 5, 6, 8でResolveを通り、combatはturn 4以降、quest advanceはturn 5で発火した。
- gatewayの503およびtimeoutは同一の安全なturn/autoコマンドで再試行し、コードで環境障害を迂回していない。テンプレート正本は変更せず、誘発用のscene参加者・HP・stakes・LLM bindingはsandbox側だけで調整した。
- 全体検証: `NO_COLOR=1 uv run pytest` → `933 passed, 1 warning in 20.95s`。`uv run ruff check .`、`uv run ruff format --check .`、`git diff --check`はいずれもpassした。
- GitNexus: `detect_changes(scope="compare", base_ref="main")`を実行し、changed 32 symbols / affected 13 processes / 10 files、aggregate risk `high`を確認した。主因は`ProjectMetrics`/`collect_metrics`のCLI・arc集計経路への波及であり、事前の個別impactはLOW、全925テストと二軸code reviewで契約を確認した。

## 完了条件

- [x] PC参加・判定・inventory・quest・combat・encounterが同一mockセッションで共存する
- [x] 各game機能のartifact、roll、event、StateDiffが既存契約へ記録される
- [x] TRPG replayがcombat、quest遷移、PC入力、encounterをGM注記として表示する
- [x] metrics JSON/CLIがgame系件数とskill check成功率を返す
- [x] mock 50ターンbenchがgame系メトリクスの退行を検知する
- [x] 実LLM 8〜12ターンでPC行動の調停、combat、questを確認し数値を記録する
- [x] テンプレート正本を実LLM誘発のために改変していない
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している
- [x] mock統合、50ターンbench、実LLMスモークがgreenで「E7ゲート通過」と判定している

## 関連ファイル

- `src/living_narrative/export_replay/trpg.py`
- `src/living_narrative/session/metrics.py`
- `src/living_narrative/cli/metrics.py`
- `tests/export_replay/test_trpg.py`
- `tests/session/test_metrics.py`
- `tests/cli/test_metrics_command.py`
- `tests/smoke/test_mist_station_50_turns.py`
- `tests/pipeline/`
- `sandbox/`（gitignored、実LLMスモークのみ）
