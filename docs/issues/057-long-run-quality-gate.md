---
id: 057
title: 実LLM長期品質ゲートと物語SLOを決定する
status: open
created: 2026-07-12
type: wayfinder:prototype
priority: P1
parent: 052
blocked_by: [053, 056]
---

# 057: 実LLM長期品質ゲートと物語SLOを決定する

## 問い

100ターン級のsessionについて、決定性・継続性・情報scope・thread収束・人物同定・反復・感情・game機能・costをどのfixtureと閾値で測り、mock／実LLM／人手評価をどう分担するか。

## 背景

現在の証跡はmock 50ターン、実LLM 20ターン、E7実LLM 8ターンまでで、β条件の100ターンは未証明。実LLM 20ターンではthread 5起票・0回収・最古19ターン、scene transition countの意味ずれが残る。character consistency true-positive、人物匿名化、motif反復、高感情分岐、rollback後の完全再現も未固定である。

## 解決条件

- sample別100ターンmock、30〜50ターン実LLM、人手読解の役割を決める
- pass/failとなる物語SLOとcost/time budgetを決める
- thread SLO、scene transitionの論理定義、narrator identity surfaceを決める
- resume／branch／rollback／export／backup/restoreを含むlong-run journeyを定義する
- provider failureやreviewを含む再現可能なbenchmark artifact方針を決める
- β gateの実LLM人手smoke(1回合格)に流用する簡易版rubricを定義する(ADR-0005 D4)

## 関連ファイル

- `docs/issues/006-turn-continuity.md`
- `docs/issues/010-emotion-homeostasis.md`
- `docs/issues/014-unresolved-thread-ledger.md`
- `docs/issues/016-character-consistency-checker.md`
- `docs/issues/019-regression-fixture.md`
- `docs/issues/038-trpg-session-e7-gate.md`
- `tests/smoke/`
- `src/living_narrative/session/metrics.py`

