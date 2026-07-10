---
id: 038
title: TRPGセッションモードとE7品質ゲート
status: in_progress
created: 2026-07-11
---

# 038: TRPGセッションモードとE7品質ゲート

## 背景

E7で追加したPC参加、能力判定、構造化inventory、quest、encounter、簡易戦闘は個別には検証済みだが、同一セッションで相互に干渉せず動くことと、長尺退行を定量検知できることはまだ固定されていない。Issue 019の50ターンregression網をgame系へ拡張し、GM向けTRPGリプレイにもゲーム進行を監査できる情報を織り込んで、E7完了の品質ゲートとする。

## 設計

1. `player_character`モードのmock統合テストで数ターンを実行し、PC行動、`dice_roll_request`、inventory use、quest open/advance/resolve、encounter、combatをそれぞれ最低1回発火させる。全state変更は既存`StateDiff`経路を通し、roll/event/interventionの関連付けと情報スコープも確認する。
2. GM向け`export_replay/trpg.py`へcombatのattacker/defender/stakes/result、quest遷移、PC入力、encounter発火の注記を追加する。既存のroll・介入表示とGM注記スタイルを維持し、通常のreader向けexport契約は変えない。
3. `session/metrics.py`とmetrics CLIへgameメトリクスを追加する。combat発生数、questのopen/advance/resolve数、PC行動反映数、encounter発火数、skill checkの成功数・総数・成功率を、applied turnと既存artifactの正本から集計する。
4. Issue 019のmock 50ターン定点でgameメトリクスをassertし、長尺退行を検知する。テスト用の誘発はmock出力・sandbox状態に限定し、テンプレート正本を改変しない。
5. `sandbox/`にmist_stationまたはorbital_echoを初期化し、OmniRoute `auto/best-coding`でplayer_characterモード8〜12ターンを実行する。PC入力がResolveで調停され、combatとquestが各1回以上動いた証跡と数値をこのissueへ記録する。

## E7ゲート判定

mock統合テスト、gameメトリクス付き50ターンbench、実LLMスモークがすべてgreenであることをE7ゲート通過条件とする。一つでも未達なら`status: done`へ変更しない。

## 完了条件

- [ ] PC参加・判定・inventory・quest・combat・encounterが同一mockセッションで共存する
- [ ] 各game機能のartifact、roll、event、StateDiffが既存契約へ記録される
- [ ] TRPG replayがcombat、quest遷移、PC入力、encounterをGM注記として表示する
- [ ] metrics JSON/CLIがgame系件数とskill check成功率を返す
- [ ] mock 50ターンbenchがgame系メトリクスの退行を検知する
- [ ] 実LLM 8〜12ターンでPC行動の調停、combat、questを確認し数値を記録する
- [ ] テンプレート正本を実LLM誘発のために改変していない
- [ ] 全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している
- [ ] mock統合、50ターンbench、実LLMスモークがgreenで「E7ゲート通過」と判定している

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
