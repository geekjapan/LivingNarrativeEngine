---
id: 134
title: RC evidence validatorのCLI summaryを提供する
status: completed
created: 2026-08-22
type: feature
priority: P1
parent: 088
blocked_by: [133]
labels: [release, real-llm, cli, privacy, v1.0.0]
---

# 134: RC evidence validatorのCLI summaryを提供する

## 背景

Issue 133により、実LLM 30ターンbenchmark JSONをreader-safeに検証するengine-layer seamができた。しかしrelease担当者がrelease候補HEADで同じ検証を実行し、release checklistへ転記するにはPython APIを直接呼ぶ必要がある。ADR-0005のCLI-first契約に従い、薄いCLI adapterを提供する。

このCLIは実LLM providerへ接続せず、artifact、Book State、rubric、checklistを変更しない。実LLMの実行、credential取得、人手R1–R8判定、著者accept/reviseを置換しない。

## 公開seam

`living-narrative release verify-real-llm-evidence --artifact <benchmark.json> --expected-revision <sha> [--json]`

- default outputは固定reason codeと安全なrevision comparisonだけを含む短いhuman-readable summaryとする。
- `--json`はIssue 133の`RealLLMBenchmarkValidation`と同じreader-safe payloadを出力する。
- validationがfailならexit 1、usage errorならexit 2、passならexit 0とする。
- narration、prompt、credential、provider URL、GM/private context、absolute path、traceback、artifact payloadをCLI outputに転記してはならない。

## 完了条件

- [x] root Typer appに`release` groupと`verify-real-llm-evidence` commandを追加する。
- [x] valid artifactでexit 0、`--json` payloadがreader-safeにround-tripする。
- [x] validation failureでexit 1かつ固定reason codeだけを出力する。
- [x] missing artifactなどusage failureでexit 2かつpath以外のartifact内容を出さない。
- [x] CLIがengine validationを再実装せず、Issue 133 public seamへのthin adapterである。
- [x] focused CLI/engine privacy回帰、全回帰（1,231 passed）、lint、format、diff checkを通す。

## 非対象

- 実LLM gatewayの起動、API key設定、実provider呼出、CIにおける実LLM実行。
- rubric R1–R8の自動評価、release checklistの自動書換え、tag/Release作成。

## 関連ファイル

- `docs/issues/133-release-evidence-validation.md`
- `src/living_narrative/release_evidence.py`
- `src/living_narrative/cli/__init__.py`
- `src/living_narrative/cli/_common.py`
- `tests/cli/test_metrics_command.py`
- `docs/real-llm-benchmark.md`
