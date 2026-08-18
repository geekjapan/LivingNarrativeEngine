---
id: 088
title: release evidence と long smoke observability を追加する
status: completed
created: 2026-08-17
type: implementation
priority: P0
parent: 059
blocked_by: []
labels: [release, quality, observability]
---

# 088: release evidence と long smoke observability を追加する

## 背景

1.0 の release contract と release checklist は install、migration、backup/restore、
replay、disclosure、plugin trust boundary、実 LLM 品質、UX を出荷条件としている。
しかし各条件の証跡、実行担当、再実行方法を一つの表で追跡する文書がない。

また Issue 071 の 100-turn mock journey は恒久 CI gate であるが、所要時間、artifact
量、状態別の進捗、失敗時の診断を構造化された report として出力しない。そのため、
長時間実行が遅いのか停止したのかを release engineering が判断しにくい。

## 目的

- release checklist のすべての項目に、状態、証跡、再実行コマンド、判定責任を対応付ける。
- 100-turn mock journey が、既存の決定性・replay・rollback・backup/restore gate を保ったまま、
  構造化された観測 report を任意の出力先へ保存できるようにする。
- report は日時を含まない決定的な内容にし、比較可能な JSON とする。

## 完了条件

- `docs/release-evidence.md` が β および 1.0 の各 gate を漏れなく列挙し、
  `pass`、`pending`、`blocked` のいずれかと、証跡、再実行方法、更新条件を持つ。
- 100-turn smoke は `LNE_LONG_SMOKE_REPORT` が指定されたとき、JSON report を出力する。
- report は turn count、elapsed seconds、workspace artifact bytes、replay bytes、
  metrics、run fingerprint を持ち、API key、prompt、GM-only data、絶対一時パスを含めない。
- report 指定あり・なしのいずれでも、既存の smoke gate の結果と決定性 assertion が変わらない。
- focused test、全 test、ruff、format、diff check を実行し、長時間 test の所要時間も記録する。

## 関連ファイル

- `.github/workflows/ci.yml`
- `tests/smoke/test_mist_station_100_turns.py`
- `docs/release-checklist.md`
- `docs/adr/0005-v1-release-contract.md`
- `docs/adr/0011-release-engineering-baseline.md`
- `docs/release-evidence.md`
- `tests/smoke/test_mist_station_100_turns.py`

## 実装結果

- `session.long_run_report` に、path/prompt/credential/stateを探索しない公開JSON writerを追加した。
- `LNE_LONG_SMOKE_REPORT` 指定時に、100-turn gateが二つのjourneyの公開metricsと決定的fingerprintを出力する。
- CI test matrixはlong-smoke reportを `actions/upload-artifact` で保存する。
- `docs/release-evidence.md` に、β/1.0 gate、status、証跡、再実行方法、更新条件を対応付けた。

## 検証結果

- `NO_COLOR=1 uv run pytest tests/session/test_long_run_report.py` — 2 passed。
- `LNE_LONG_SMOKE_REPORT=/tmp/lne-long-smoke-report.json NO_COLOR=1 uv run pytest tests/smoke/test_mist_station_100_turns.py` — 1 passed、185.67秒。二journeyのfingerprint一致、report内絶対pathなし。詳細は `docs/evaluations/2026-08-17-issue088-long-smoke-observability.md`。
- `NO_COLOR=1 uv run pytest` — 1069 passed、2 skipped、231.09秒。
- `uv run ruff check .`、`uv run ruff format --check .`、`git diff --check` — PASS。
- GitNexusの再解析は依存パッケージの対話的build承認を要求して停止した。コード変更前・commit前に二回非対話実行を試みたが、tooling環境要因でimpact reportは取得できなかった。

## 検証計画

1. report の unit/focused smoke を temp path で実行し、公開可能な schema と必須値を検査する。
2. 同一 seed の二回実行で replay/artifact fingerprint が一致する既存 assertion を維持する。
3. `LNE_LONG_SMOKE_REPORT` 未指定で report を作らないことを確認する。
4. CI では report artifact を upload し、失敗時も診断を残せるようにする。

## 非目標

- 1.0 をこの Issue 単独で release すること。
- 実 LLM の credentials を CI または report に追加すること。
- 既存の 100-turn test をより短い test に置き換えること。
- book/chapter schema をこの Issue に含めること。
