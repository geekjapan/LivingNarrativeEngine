---
id: 085
title: 1.0向け実LLM 30ターン品質gateを実行する
status: done
created: 2026-07-14
type: release-validation
priority: P1
parent: 057
blocked_by: []
---

# 085: 1.0向け実LLM 30ターン品質gateを実行する

Issue 072の手順とADR-0010に従い、実LLM 30ターンrunを実行して1.0品質gateの
機械証跡と人手rubricを確定する。

## 完了条件

- [x] `mist_station`を固定seedで30ターン実行し、turn 15から16のresumeを確認する。
- [x] provider failure、turn欠落、未完了turnがないことを確認する。
- [x] canonical benchmark JSON、reader-visible Markdown、metricsを保存する。
- [x] ADR-0010の機械SLOとR1–R8人手rubricを判定し、PASS/FAILを記録する。
- [x] release checklistの実LLM品質gateへ証跡を紐付ける。

## 関連ファイル

- `docs/real-llm-benchmark.md`
- `docs/beta-quality-gate-rubric.md`
- `docs/evaluations/`
- `docs/release-checklist.md`

## 実行結果

- run ID: `20260714-issue085-mist-station-v1`
- result: `FAIL`
- turn 1–7: `applied`
- turn 8: act phaseの`ProviderConnectionError`で`failed`
- resume: checkpoint turn 15へ未到達のため未実施
- gateway: failure後に`127.0.0.1:20128`への疎通不能を確認

同じrunは修復せず、別run IDで再実行した。

## 再実行

- run ID: `20260714-issue085-gpt56-luna-low-v2`
- model: `cx/gpt-5.6-luna-low`
- seed: `issue-085-mist-station-v1`（v1と同一）
- status: `FAIL`（30/30 applied、provider failureなし、resume成功）
- machine SLO: pacing `15 > 3`、thread opened/resolved `0/0`でFAIL
- human rubric: R1（継続性）、R3（thread回収）、R5（反復）でFAIL
- resources: 60 calls、465,052 tokens、model pricing未登録

## 証跡

- `sandbox/20260714-issue085-mist-station-v1/benchmark.json`
- `sandbox/20260714-issue085-mist-station-v1/metrics.json`
- `docs/evaluations/2026-07-14-20260714-issue085-mist-station-v1-benchmark.md`
- `docs/evaluations/2026-07-14-20260714-issue085-mist-station-v1-human-rubric.md`
- `sandbox/20260714-issue085-gpt56-luna-low-v2/benchmark.json`
- `sandbox/20260714-issue085-gpt56-luna-low-v2/metrics.json`
- `docs/evaluations/2026-07-14-20260714-issue085-gpt56-luna-low-v2-benchmark.md`
- `docs/evaluations/2026-07-14-20260714-issue085-gpt56-luna-low-v2-human-rubric.md`
