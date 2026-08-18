---
id: 103
title: 長編Benchmark Harness
status: in_progress
created: 2026-08-18
---

# 長編Benchmark Harness

## 背景

一章の成功では、数十万文字級の長編を自律制作できることを示せない。代表Story Bibleに対する反復可能な長編制作試験で、plan進行、continuity、quality、budget、recovery、exportの証跡を同じreport形式で測定する必要がある。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| 複数のStory Bible fixtureを同一harnessで実行できる | benchmark integration test |
| chapter数、accept/revise/block、token、cost、artifact fingerprintを集計する | report schema test |
| providerなしの決定的mock modeで30章相当の状態遷移を検証できる | long-run test |
| recoveryとbudget circuit-breakerの発火を別scenarioで測定できる | resilience test |
| public reportは絶対path、prompt、secret、provider credentialを含まない | disclosure test |
| reportはJSONとしてatomicに書き出され、CI artifact化可能である | writer test |

## 関連ファイル

- `src/living_narrative/book/benchmark.py`
- `src/living_narrative/session/long_run_report.py`
- `tests/book/test_benchmark.py`
- `tests/smoke/test_long_form_benchmark.py`

## 非対象

商業編集者のブラインド評価、実LLMによる90/200章の費用実測、CI時間枠外の長時間実行はharnessの出力を用いる運用フェーズで扱う。
