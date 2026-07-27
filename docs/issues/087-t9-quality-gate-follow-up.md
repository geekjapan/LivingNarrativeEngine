---
id: 087
title: T9再実行で残ったthread寿命・narrator fallback・反復を解消する
status: completed
created: 2026-07-22
type: implementation
priority: P1
parent: 057
blocked_by: [086]
labels: [ready-for-agent]
---

# 087: T9再実行で残ったthread寿命・narrator fallback・反復を解消する

## 背景

Issue 086のfallback開始条件修正後、T9を`20260722-issue086-fallback-fix`として再実行した。
30/30ターン、resume、replay、pacing、thread resolved ratioは合格したが、次の残件により
総合判定は`FAIL`となった。

- narratorがturn 1で開いたemergent threadが未回収のまま`max_open_turns=29`となった
  （上限25）。
- turn 21で`StructuredOutputError`が発生し、renderer fallbackが1件記録された。
- 人手rubric R5で、「合図まで待つ／追跡者を警戒する／水滴を数える」の同義反復が
  3ターンを超えて継続した。

## 完了条件

- narratorが開いたthreadを期限内にadvanceまたはresolveでき、実LLM 30ターンrunで
  `max_open_turns <= 25`を満たす。
- narratorのstructured output失敗を回帰テストで再現し、T9再実行でrenderer fallbackを
  発生させない。
- authored Action Outcomeがnarrationへ反映され、同義の待機・警戒描写が3ターンを超えて
  連続しない。
- 同一seed、model、bindingでT9を再実行し、機械gateと人手rubric R5がPASSする。
- 30/30ターン、turn 15→16 resume、replay match 1.0、reader-visible leak 0を維持する。
- 実装変更には、その変更なしでは失敗する最小のregression testを追加する。

## 関連ファイル

- `docs/issues/086-state-backed-action-outcomes.md`
- `docs/issues/086-delivery-plan.md`
- `docs/evaluations/2026-07-22-20260722-issue086-fallback-fix-benchmark.md`
- `docs/evaluations/2026-07-22-20260722-issue086-fallback-fix-human-rubric.md`
- `sandbox/20260722-issue086-fallback-fix/benchmark.json`
- `src/living_narrative/agents/pacing.py`
- `src/living_narrative/narration/`
- `tests/agents/`
- `tests/narration/`

## R1実装

- narrator由来のthreadは25ターン経過時に未更新ならresolveし、作者定義threadには適用しない。
- thread originはID形式ではなく、append-onlyなopening `thread_update` Eventの`cause`から判定する。
- narratorのstructured output失敗時はrendererへ落とす前に同じreader-safe入力で1回再実行する。
- mist_stationのauthored fallback actionをreader-visibleにし、Action Outcomeをnarrationへ渡す。

## R4受入結果

- run ID: `20260727-issue086-r4-hardening`
- 機械SLO: `PASS`。30/30 applied、resume、replay 1.0、max open turns 1、fallback 0、
  scene transition 1、elapsed 868.476秒、LLM calls 90、total tokens 487,284、leak 0。
- 人手rubric: Claude Fable 5が独立読解し、R1–R8をすべてYESと推奨した。R5の同義反復を
  最大の不確実点として明示したうえで、ユーザーが判定に同意した。
- 証拠: `sandbox/20260727-issue086-r4-hardening/benchmark.json`、
  `docs/evaluations/2026-07-27-20260727-issue086-r4-hardening-benchmark.md`、
  `docs/evaluations/2026-07-27-20260727-issue086-r4-hardening-human-rubric.md`
- 完了条件をすべて満たしたため、本Issueを`completed`とする。
