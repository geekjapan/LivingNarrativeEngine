---
id: 086-delivery-plan
title: Issue 086 delivery DAG（ticket分解）
status: approved
created: 2026-07-20
parent: 086
depends_adr: 0013
---

# Issue 086 delivery plan — ticket分解

Issue 086を9ノードのDAGへ分解する。ADR-0013の契約（D1–D8）を正本とする。
各ノードは独立レビュー可能な単位。書込scopeが重なるノードは同一waveに置かない。

## DAG概要

| ID | ノード | blocked_by | user story | 並列安全 |
|----|--------|-----------|-----------|---------|
| T1 | schema基盤 | ADR-0013 | 2,6,7 | 単独wave |
| T2 | Resolver + Outcome→StateDiff | T1 | 1,3 | wave2 |
| T3 | stall fallback + pacing事前検証 | T2 | 4,5 | wave3 |
| T4 | encounter recurrence | T1 | 6 | wave2 |
| T5 | authored thread lifecycle | T2 | 7 | wave3 |
| T6 | visibility/秘密情報 hardening | T2,T4,T5 | 9 | wave4 |
| T7 | benchmark配線（narrator bind + artifact log） | T1 | 8 | wave2 |
| T8 | regression seam（backfill廃止 + 敵対的test） | T2,T3,T4,T5,T6,T7 | 3,10 | wave5 |
| T9 | 実LLM 30ターン受入gate | T1..T8 | 全体 | wave6（人間/runtime gate） |

### 実行wave

- wave1: T1
- wave2: T2, T4, T7（書込scope非重複）
- wave3: T3, T5
- wave4: T6
- wave5: T8
- wave6: T9（`cx/gpt-5.6-luna-low`到達性が前提。手動/runtime受入のため人間確認ゲート）

依存はほぼ直列で並列余地は小さい。これは本Issueが元々アーキテクチャの積み上げであることを反映する。

---

## T1: schema基盤

- 目的: ADR-0013 D1/D3/D4/D7のschemaを後方互換で追加する。behavior変更は含めない。
- 変更: 新`Affordance`/`Outcome`モデル、`ActionCandidate`に`affordance_id`（optional）、`EncounterEntry`に
  `recurrence`（once/cooldown/unlimited、既定=cooldown≥pacing window）、`UnresolvedThread`に明示status
  （open/advanced/resolved）と`resolved_turn`、affordance YAMLの読込（`state/affordances.yaml`をoptional loadで）。
- 主ファイル: `src/living_narrative/state/models.py`、`src/living_narrative/state/store.py`、
  `src/living_narrative/agents/models.py`、`src/living_narrative/narration/models.py`。
- 受入: Pydantic v2 validation、YAML `snake_case`、既存project/replayが壊れない（optional/default）。schema round-trip test。
- 注意: scene/encounterはroot-add不可の制約を維持。既存の保存済みreplayは変更しない。

## T2: Resolver + Outcome→StateDiff

- 目的: D1/D2/D3。Intent→affordance照合、前提/競合/seeded roll評価、成立Outcomeを認定advancement StateDiffへ。
- 変更: `conflict_resolver.resolve_conflicts`にaffordance照合とOutcome生成、`record_roll`でroll保存、reject理由artifact。
  `state_manager._changes_for_event`にOutcome→StateDiff分岐（scene遷移/end、reader/canon fact、quest、thread、combat）。
  `character`はaffordance IDをIntentに載せる。自由文Actionは従来どおり保存。
- 主ファイル: `src/living_narrative/agents/conflict_resolver.py`、`src/living_narrative/agents/state_manager.py`、
  `src/living_narrative/agents/character.py`。
- 受入: 同一state/seed/Intent列で同一Outcome/roll/StateDiff（determinism test）。非合致Intentは状態不変+reject artifact。
  成立Outcomeが次ターンのscene状態へ反映される（integration）。

## T3: stall fallback + pacing事前検証

- 目的: D5/D6。fallback判定をResolveまで遅延、通常Outcome優先、`pacing_exhausted`診断、実行前validation。
- 変更: `pacing.py`のstall判定連携、fallback affordance発火（Resolve）、`state/validation.py`にpacing宣言検証、
  `pipeline/driver.py`の停止/失敗経路へ`pacing_exhausted`を接続（新meta status不追加、review/failed契約再利用）。
- 主ファイル: `src/living_narrative/agents/pacing.py`、`src/living_narrative/agents/conflict_resolver.py`、
  `src/living_narrative/state/validation.py`、`src/living_narrative/pipeline/driver.py`。
- 受入: fallback非在/消費済みで`pacing_exhausted`。Outcome成立ターンにfallback二重発火なし。fallbackもseed/replay一致。
  固定ターンbenchが早期終端したらFAIL。

## T4: encounter recurrence

- 目的: D7。once/cooldown/unlimitedのeligibilityをEvent履歴から決定。
- 変更: `world_simulator._encounter_is_eligible`/`_encounter_events`にpolicy評価、`event_history`が`encounter_id`を参照可能に。
  同一ID連続ターン抑止、代替なしならencounter無し。policy未指定=cooldown≥pacing window。
- 主ファイル: `src/living_narrative/agents/world_simulator.py`、`src/living_narrative/agents/event_history.py`。
- 受入: 各policyのeligibility test、連続発火抑止test、過去replay不変。

## T5: authored thread lifecycle

- 目的: D4。authored thread open/advance/resolveを一次正本とし、narrator提案より先に適用、競合はauthored優先・重複open拒否。
- 変更: `state_manager._thread_update_changes`をauthored effect優先へ、narrator dedup/precedence、
  resolved threadへのadvance等の矛盾をreject理由付き保存。`resolved_turn`記録。
- 主ファイル: `src/living_narrative/agents/state_manager.py`、`src/living_narrative/narration/`（narrator提案の後段）。
- 受入: authored/narrator競合dedup test、矛盾reject test、authored更新ターンのnarrator重複open拒否test。

## T6: visibility/秘密情報 hardening

- 目的: D（story 9）。Intent/affordance/Outcome/thread/narrator contextの全経路で情報scope維持。
- 変更: `context_builder`（character prompt）と`narration/context`（narrator prompt）のfilterへ新経路を通す。
  hidden affordanceのID/条件を未認知characterへ渡さない、reader不可Outcomeからreader thread開かない、
  reject artifactに秘密の値を残さない。CLI/web/bench artifactにGM情報を含めない。
- 主ファイル: `src/living_narrative/agents/context_builder.py`、`src/living_narrative/narration/context.py`、
  reject/outcome artifact writer。
- 受入: leak test（hidden affordance/thread/GM情報がpromptとartifactに出ない）、`/security-review`該当なら実施。

## T7: benchmark配線（narrator bind + artifact log）

- 目的: D8のうちコード変更分。narratorを指定モデルへbindできる配線、narrator mode/call数/fallbackのartifact記録、
  binding-only baselineを新run IDで取得可能にする。
- 変更: template `project.yaml`のnarrator binding、`docs/real-llm-benchmark.md`手順のbinding明記、
  narrator mode/call数のartifact集約（`mode`は既存記録を利用、call数集計を追加）。
- 主ファイル: `src/living_narrative/templates/mist_station/`（project config）、`docs/real-llm-benchmark.md`、
  narrator record集約点。
- 受入: bind時に`mode: llm`とcall数がartifactで確認できる。renderer fallback時にturn/理由/modeが残る。

## T8: regression seam（backfill廃止 + 敵対的test）

- 目的: story 3/10 + Testing Decisions。実runtime経路でSLOを満たす回帰seamへ移行。
- 変更: `tests/smoke/test_mist_station_100_turns.py:58`と`..._50_turns.py:53`のthread/quest backfillを除去。
  mist_station templateに作者定義affordance/fallback/authored threadを追加し、実経路でthread open/advance/resolveと
  scene進展を発生させる。敵対的integration test追加（fallback発火、`pacing_exhausted`、二重発火なし、encounter各policy、
  authored/narrator thread競合dedup、hidden情報leakなし、同一seedでEvent/roll/StateDiff完全一致）。
  replay 2回一致・rollback・15→16 resume・backup restoreを維持。
- 主ファイル: `tests/smoke/*`、`tests/integration/*`（新規）、`src/living_narrative/templates/mist_station/state/*`。
- 受入: `max_consecutive_stall_turns <= 3`、thread resolved/opened比、max open turns、visibility、game機能発火を
  実経路で満たす。backfillなしで100/50ターンgateがpass。全test/lint/format/diff check green。

## T9: 実LLM 30ターン受入gate

- 目的: ADR-0010最終受入。`cx/gpt-5.6-luna-low`をcharacter+narratorにbindした30ターンrun。
- 手順: `docs/real-llm-benchmark.md`に従い固定seedで実行、turn15→16 resume確認、canonical JSON/Markdown/metrics保存、
  機械SLOとR1–R8をPASS/FAIL判定、release checklistへ紐付け。
- 前提: OmniRoute gateway `127.0.0.1:20128`到達性。手動/runtime受入のため**人間確認ゲート**。
- 受入: 機械SLOとR1–R8がすべてPASS。FAILなら診断を添えてIssue 086へ差戻し。

---

## 承認事項（人間）

1. ADR-0013 D1–D8の契約。
2. 上記9ノードの分解粒度と依存（wave構成）。
3. T9（実LLM受入）を自動delivery外の人間ゲートとして扱う点。
4. mist_station templateへの作者定義affordance/fallback追加（既存template更新）を許容する点。

## 実行結果

- T1–T8: PR #27（`7f62ecc`）でmerge済み。Python 3.12/3.13、security-quality、
  clean-install acceptanceのCIは成功。
- T7補完: 2026-07-21にbenchmark手順とartifact templateへnarrator binding/call/fallback契約を追加。
- T9: `20260721-issue086-post-implementation`を実行し`FAIL`。30/30 applied、15→16 resume、
  narrator 30 calls / fallback 0、replay 1.0は成功したが、pacingとthread SLO、R3/R5が未達。
- T9 rerun: fallback開始条件修正後の`20260722-issue086-fallback-fix`も`FAIL`。pacingとR3は
  改善したが、thread max-open、narrator fallback、R5が未達。
- parent Issue 086は`in_progress`を維持し、診断と証跡を同Issueへ記録した。
