---
id: 019
title: 50ターンregressionフィクスチャ + metricsコマンド(品質退行の検知網、Track Aゲート)
status: done
created: 2026-07-07
---

# 019: 50ターンregression + metrics

## 背景

DAG Track Aのゲートノード(E7着手条件)。Phase 5完了条件「50ターン以上のセッションを維持できる」「regression fixtureで品質低下を検知できる」。dynamics一式(006〜016)が入った今、長尺での不変条件を自動検証する網を張る。

## 設計

1. **`living-narrative metrics --project P [--json]`**(CLI新設): 実行済みランのartifacts/stateから品質メトリクスを集計:
   - turns: 総数・status内訳・失敗/discard/rolledback数
   - emotions: キャラ×感情ごとの min/max/final/天井(100)张り付きターン数
   - pacing: pacing_stallイベント数・停滞最長連続
   - threads: open/advance/resolve件数、未回収スレッドの最長放置ターン
   - threats: pressure推移(初値/終値/stage発火ターン)
   - scenes: 遷移回数、activeシーン数の推移異常(0や2+)
   - checks: checker別findings件数
   - memory: summary生成数
2. **mock 50ターンregressionテスト**(`tests/smoke/test_mist_station_50_turns.py`、既存20ターンsmoke拡張 or 別ファイル): 50ターン実走(mock)後、metricsロジックを直接使い不変条件をassert:
   - 全ターンapplied(review経由含む)、timeline=50
   - 感情が全ターン0-100内、**50ターン中の天井張り付きが連続10ターン未満**
   - activeシーンが常に1(遷移瞬間を除く)
   - checker error 0件
   - RNG会計整合(resume可能)
   - 実行時間ガード(mockで60秒以内 — 性能退行検知)
3. metrics実装は `session/metrics.py`(collector)+ CLI薄皮。webのgm APIから将来再利用可能な形に

## 完了条件

- [x] metricsコマンドが既存sandboxラン(issue015_llm等)で妥当な集計を返す
- [x] mock 50ターンテストがpassし、不変条件違反を仕込むと落ちることをspot確認
- [x] mock全テストpass(604+)、50ターンテストは1分以内
- [x] 実LLM 20ターン定点ラン(`sandbox/bench20_llm`、2026-07-07): 20/20 applied、感情0-100内・天井張り付きゼロ、checker findings全ターンゼロ、threat 0→100(stage 3/7/11/14ターン)、turn 14シーン遷移、summary 2回。ゲート通過。フォロー候補: metricsのtransition_countがfield-write数を数える(論理遷移1→2表示)、スレッド回収圧不足(5起票0回収・最古19ターン)

## 関連ファイル

- 新規: `src/living_narrative/session/metrics.py`、`src/living_narrative/cli/metrics.py`、`tests/smoke/test_mist_station_50_turns.py`
- 参照: `tests/smoke/test_mist_station_20_turns.py`(実走パターン)、各stateスキーマ
- DAG: `docs/plan/feature-dag.md`
