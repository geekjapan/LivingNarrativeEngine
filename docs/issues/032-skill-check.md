---
id: 032
title: stats/skillsを用いた判定ルール
status: done
created: 2026-07-11
---

# 032: stats/skillsを用いた判定ルール

## 背景

Issue 031で `CharacterState` に能力値と技能を保存・表示できるようになったが、ゲーム内の判定にはまだ利用されていない。既存の再現可能な `RandomEngine.roll_chance` と介入の `dice_roll_request` を拡張し、難易度とキャラクター能力から導く修正値を持つ判定を、既存のroll/event記録規約を保ったまま実行できるようにする。

## 設計

1. 判定難易度を成功目標値として明示し、指定したstat/skillの値から名前付きmodifierを導出して `roll_chance` へ渡す。欠落能力・不正な要求は境界で明確に検証する。
2. `dice_roll_request` の既存介入経路を通してキャラクター判定を要求できるようにし、従来形式との後方互換を維持する。
3. 判定の `RollRecord` は既存形式で `rolls.yaml` へ保存し、対応するイベントの `roll_ids` にD121準拠で紐付ける。
4. `state/models.py` への追加は避け、ランタイムstate変更が生じる場合は必ず `StateDiff` 経由とする。

## 完了条件

- [x] stat/skillから決定的なmodifierを導出し、難易度targetを含む判定を実行できる
- [x] `dice_roll_request` から判定要求でき、既存の単純dice要求も壊さない
- [x] 判定結果が既存形式の `rolls.yaml` に記録される
- [x] 対応イベントに判定の `roll_ids` が設定される
- [x] 欠落キャラクター・欠落能力・境界値・再現性のテストがある
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/random/engine.py` (`RandomEngine.roll_chance`)
- `src/living_narrative/intervention/schema.py`
- `src/living_narrative/intervention/router.py`
- `src/living_narrative/agents/world_simulator.py`
- `src/living_narrative/agents/conflict_resolver.py`
- `src/living_narrative/pipeline/` (roll/event永続化)
- `tests/test_chance.py`, `tests/agents/`, `tests/pipeline/`
