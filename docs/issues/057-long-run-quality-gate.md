---
id: 057
title: 実LLM長期品質ゲートと物語SLOを決定する
status: review
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


## 決定案(2026-07-13、承認待ち)

事実確認(最重要): **rollback後RNG再現は「条件付き再現」**。RNG stateはseed+`rng_draws_consumed`のreplay方式(`random/engine.py:40-45`)、rollbackはRNGを直接触らず`turn_NNNN_rolledback_`へのrenameが集計対象から外れる副次効果で巻き戻る(`rollback.py:69-90`、`rng_state.py:11-31`)。構造上は決定論的だが**rollback→次turn実行でroll列一致をassertする結合testが存在しない**。transition_countはfield-write数計上で論理遷移の約2倍(`metrics.py:451-466`、testコメントで追認済み)。実LLM自動テストはCI上ゼロ件。

### 決定

- (a) **役割分担**: mock 100ターン=CI常設回帰gate(機械pass/fail)/実LLM 30ターン=β・1.0 gate時+リリース前定点観測(CI常設しない。50ターンは費用対効果でmust外)/人手読解=実LLMラン抜粋15ターン(冒頭5・中盤5・終盤5)をrubric判定。
- (b) **gate SLO(機械閾値)**: replay完全一致(mock 100×2回)/rollback後RNG決定性(結合test)/`max_consecutive_stall_turns`≤3/thread resolved比≥0.5かつ`max_open_turns`≤25/leak findings(critical/high)=0/`max_consecutive_at_ceiling`≤5/game機能発火>0/論理遷移数比率/cost・time budget項目の存在(初期値は仮固定、運用調整可)。**観測のみ(gate外)**: 人物同定・narrator identity(人手rubricへ)、motif反復(同)、consistency true-positive率。
- (c) thread SLO=既存open/advance/resolveの3状態遷移をそのまま定義採用。**scene transition論理定義=旧+新のstatusペア1組で1カウント**(metrics.py修正+既存test期待値更新)。narrator identity surface=「読者から話者・視点が一意同定可能」、1.0は人手項目。
- (d) **long-run journey**: init→40turn→export→snapshot→41-60介入分岐→60で55へrollback→再進行→80-100→最終export→backup-restoreから別プロセスresume。既存20-turn(resume)+rollback testパターンの合成のみ、新機構なし。
- (e) **benchmark artifact**: 現行019運用踏襲(sandbox実行+JSON+`docs/evaluations/`へmd転記)。provider failureはfail扱い+発生turn記録。転記半自動CLIはshould。
- (f) **β人手rubric(8項目YES/NO、1つでもNOでfail)**: 継続性矛盾なし/GM情報漏洩なし/thread≥1回収/人物同定/同一フレーズ3連続反復なし/感情整合/game機能≥1発火/rollbackまたはresume正常動作。

### 分類

must=rollback-RNG結合test(D3(ii) replay契約+(iii))、transition_count定義修正(閾値運用前の公開契約固定)、100ターンmock SLO gate、実LLM30ターンbench+rubric(D4直接要求)/should=人物同定・motif定量化、cost初期値調整余地、転記自動化/post-1.0=memory summary質測定、checker文体拡張。

### ADR候補

- **ADR: 実LLM長期品質ゲートと物語SLO** — (a)-(f)を契約固定。rollback-RNG mustとtransition定義変更(破壊的)を明記。ADR-0005 D4の「057 rubric簡易版」参照先。

### 実装Issue分割

Q1: SLO測定基盤(metrics拡張+transition修正+rollback-RNG結合test)/Q2: 100ターンmock fixture CI常設(Q1依存)/Q3: 実LLM30ターンbench手順+artifact/Q4: β/1.0 rubric文書。(番号は062で採番)
