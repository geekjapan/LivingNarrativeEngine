---
id: 036
title: 状態条件付きencounter table
status: in_progress
created: 2026-07-11
---

# 036: 状態条件付きencounter table

## 背景

World Simulatorは背景イベント、threat、factionを生成できるが、シーンや世界状態に応じた遭遇候補をデータ駆動で誘発できない。既存の決定論的weighted tableとroll記録を再利用し、テンプレートごとのencounterを追加コードなしで定義できるようにする。

## 設計

1. text、正のweight、visibility、任意のscene_idまたはthreat条件を持つPydantic v2 encounter entryを追加する。`encounters.yaml`はoptional load/saveとし、既存projectは空tableで動作を変えない。
2. World Simulatorで現在のactive sceneとthreat状態に合うentryだけをeligibleにし、存在するときだけ`RandomEngine.select_from_table`で1件を選ぶ。eligibleがなければRNG drawを消費しない。
3. encounter selectionはtable rollとして`_roll`をevent effectsへ含め、既存pipelineが`rolls.yaml`へ記録する。eventはentryのvisibilityを保持し、State Managerの既存event→diff経路だけを使う。
4. threat/faction/background eventの順序と挙動を変えず、encounter eventを独立typeとして追加する。
5. mist_stationとorbital_echoへ、条件によりeligible/非eligibleになる実値を追加する。

## 完了条件

- [ ] encounter entryと`encounters.yaml`のoptional load/save経路がある
- [ ] active sceneまたは軽量threat条件でeligible entryを絞り込める
- [ ] eligible entryだけを既存weighted tableで決定論的に選ぶ
- [ ] selection rollがeventのroll idと`rolls.yaml`へ既存形式で記録される
- [ ] encounter visibilityが保持され、状態変更は既存`StateDiff`経路だけを使う
- [ ] mist_stationとorbital_echoの両templateに実値がある
- [ ] missing-file後方互換、RNG再現性、条件不一致をテストしている
- [ ] 全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/state/models.py`
- `src/living_narrative/state/store.py`
- `src/living_narrative/state/schema_export.py`
- `src/living_narrative/agents/world_simulator.py`
- `src/living_narrative/random/engine.py`
- `src/living_narrative/templates/mist_station/`
- `src/living_narrative/templates/orbital_echo/`
- `tests/agents/test_world_simulator.py`
- `tests/test_state_model.py`
