---
id: 133
title: 実LLM release evidenceのreader-safe validatorを実装する
status: completed
created: 2026-08-22
type: feature
priority: P1
parent: 088
blocked_by: [072]
labels: [release, real-llm, quality-gate, privacy, v0.9.0]
---

# 133: 実LLM release evidenceのreader-safe validatorを実装する

## 背景

ADR-0005はv1.0の品質gateとして実LLM 30ターンと人手rubricを要求し、Issue 088はrelease候補HEADでの再実行を要求する。現行手順は詳細だが、benchmark JSON・human rubric・git revision・provider failure・privacy規約の整合を機械的に確認するpublic seamがない。そのため、release担当者は人手でartifactを読み合わせる必要があり、途中停止、revision drift、禁止情報の混入を見落とす余地がある。

このIssueは実LLMの実行、credential取得、rubricの代行判定、著者accept/reviseを自動化しない。artifactが提出された後に、reader-safeな機械契約だけを検証する。

## 公開seam

`validate_real_llm_benchmark_artifact(path, expected_revision) -> RealLLMBenchmarkValidation`をpublic seamとする。

入力はIssue 072の`real_llm_benchmark` JSON artifactとする。出力は`passed`、固定reason code、`completed_turns`、`expected_revision`/`observed_revision`の安全なcomparisonだけを持つ。artifact内のnarration、reader-visible state、prompt、credential、provider URL、absolute path、GM/private context、tracebackを出力へ転記してはならない。validatorはartifactを変更しない。

## 完了条件

- [x] schema version / artifact type / run status / 30ターン連番 / completed turn count / provider failure / narrator fallback / narrator call count / resume checkpoint / leak scanを検証する。
- [x] `expected_revision`とartifact revisionの不一致を固定reason codeでfailにする。
- [x] prompt、credential付きprovider URL、GM/private context、absolute path、tracebackに相当する禁止値を、内容を返さない固定reason codeでfailにする。
- [x] valid artifact、途中停止、revision mismatch、provider failure、narrator fallback、resume failure、leak scan failure、privacy violation、unsafe pathをpublic seamでTDD回帰にする。
- [x] 検証結果はreader-safeで、Book State、run artifact、rubric、release checklistを変更しない。
- [x] 既存のmock 100ターン/Book benchmark/CI回帰を壊さない（local全回帰 1,227 passed、CIで継続確認）。

## 非対象

- 実LLM gatewayの起動、API keyの設定、providerへの実行、CIでの実LLM常時実行。
- human rubric R1–R8の自動判定、著者accept/reviseの自動化、release tagの作成。
- Book State / project schema migration。

## 関連ファイル

- `docs/adr/0005-v1-release-contract.md`
- `docs/adr/0010-quality-gate-narrative-slo.md`
- `docs/real-llm-benchmark.md`
- `docs/release-checklist.md`
- `docs/issues/088-v1-release-closeout.md`
- `docs/issues/089-rc-gate-execution-unblock.md`
- `docs/evaluations/real-llm-benchmark-template.json`
