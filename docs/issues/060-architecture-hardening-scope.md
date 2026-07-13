---
id: 060
title: 1.0前に解消するarchitecture debtの範囲を決定する
status: done
created: 2026-07-12
type: wayfinder:research
priority: P1
parent: 052
blocked_by: [055]
---

# 060: 1.0前に解消するarchitecture debtの範囲を決定する

## 問い

transaction/recovery契約を実装しやすくし、今後の変更リスクを下げるために、import cycleと責務集中のどこまでを1.0前に分割し、どこを計測付きでpost-1.0へ送るか。

## 背景

GitNexusは`character→llm_gateway→plugins→pipeline registry→agent slots→character`と`character consistency checker↔safety registry`の2 cycleを検出した。`state_manager.py` 899行、`web/service.py` 792行、`web/page.py` 746行、`TurnPipeline.run`約280行に責務が集中する。ただし全面refactorはrelease riskになり得る。

## 解決条件

- transaction coordinatorを置くmodule境界を決める
- import cycleを解く依存方向を決める
- state reducer、web job coordinator、UI分割のrelease blocker範囲を決める
- refactor前後のbehavior／impact／performance検証を決める
- 削除・抽出・延期を優先順位つきで記録する

## 関連ファイル

- `src/living_narrative/pipeline/driver.py`
- `src/living_narrative/agents/state_manager.py`
- `src/living_narrative/web/service.py`
- `src/living_narrative/web/page.py`
- `src/living_narrative/plugins/sdk.py`
- `src/living_narrative/safety/registry.py`


## 決定(2026-07-13承認済)

事実確認: cycle 1(character→…→agent slots→character)は5 edge中3つがlazy/TYPE_CHECKINGで意図的な依存逆転(D108/D113)、実行時ImportErrorなし=実害は設計品質のみ。cycle 2(consistency checker↔safety registry)は`registry.py:85-97`の無コメントlazy importが実際に機能している回避策で、`Finding`等の型の置き場所の問題(相互依存ではない)。`page.py`はロジックなしの単一HTML定数。commit順序ロジックが`driver.py`と`review.py`に重複している。

### 決定

- (a) **transaction coordinator境界**: 新設`state/transaction.py`(state層leaf)。`project_lock()`/`commit_state_diff()`(hash→intent fsync→save→artifactsを1関数集約)/`classify_recovery_state()`。driver commit phaseとreview.pyが同一moduleをimport=重複解消。055 Issue Aの実装場所として確定。
- (b) **cycle解消方向**: cycle 1=`default_registry()`を`agents/slots.py`側へ移設(SlotRegistryクラスは残す)。cycle 2=`safety/types.py`へ`Finding`等を抽出しregistryのlazy import撤廃。**いずれも1.0ではやらない**(下記(c))。
- (c) **release blocker範囲(must)**: transaction.py新設+driver/review統合、settings書込lock統合、auto-run coordinatorのlock統合+`web/auto_run.py`抽出(055が同じ行を触るためbundle、追加コストほぼゼロ)。**post-1.0(計測付き延期)**: cycle 1・2解消(CI cycle検出観測、cycle 2優先)、state_manager.py分割、web/service.py残り分割。**非候補**: page.py(054/058既決定)。
- (d) **検証**: 各抽出後にGitNexus detect_changes+impact report、既存全test緑を合否基準(純粋移動はbehavior-preserving)。auto-run lock競合の統合test 1本のみ新規。性能はflock 1 syscall/mutationで無視可、専用ベンチ不要。
- (e) 優先順位: §2(e)の10項目リスト(must 5→should/post 4→非候補1)。

### ADR候補

- **ADR: 1.0前architecture debt範囲の凍結** — transaction.pyを全mutation経路の唯一のcommit順序境界とする、cycle/行数はCI観測に留めpost-1.0 gate化、分割scopeは055が触る範囲のみ。055のADR(lock/journal/recovery契約)とは二本立てで相互参照。

### 実装Issue分割

- transaction.py境界は055 Issue Aの実装詳細として吸収(新issue不要)
- 新issue: web/service.py settings/auto-run lock統合+auto_run.py抽出(must、055-Aと並走)
- 新issue×4(post-1.0): cycle 1解消/cycle 2解消/state_manager分割/service残り分割(CI計測gate導入後)
