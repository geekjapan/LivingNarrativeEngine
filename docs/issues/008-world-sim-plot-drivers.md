---
id: 008
title: World Simulatorにプロットドライバーが無い(脅威が永遠に「接近中」のまま)
status: done
created: 2026-07-06
---

# 008: 脅威エスカレーショントラック

## 背景

20ターン評価(`docs/evaluations/2026-07-06-replay-20turn-eval.md`)の最重要所見: 136イベント中プロットイベント0。World Simulator(`world_simulator.py:16`)はテーブル駆動の環境音のみで、gm_vault/hidden_factsの真実(追跡者・封印施設)は一度も作動しない。足音は20ターン「近づき続けて」到着しない。物語を前に進める力学がエンジンに存在しない。

## 設計

データ駆動の**脅威エスカレーショントラック**。エンジンは汎用機構のみ、物語固有の内容はテンプレートYAMLに置く(Issue 005の背景イベントテーブルと同じ分担)。

```yaml
# world.yaml
threats:
  - id: threat_001
    name: 追跡者
    pressure: 0              # 0-100、可変状態(diff経由でのみ更新)
    pressure_per_turn: 2d6   # dice記法、seeded RNGで毎ターン加算
    stages:
      - at: 25
        text: 足音の方向が特定できるようになった…
        visibility: scene
      - at: 50
        text: 霧の中に人影が一瞬見える…
        visibility: reader
      - at: 100
        text: 追跡者が姿を現す…
        visibility: reader
        effects: {encounter: threat_001}
```

- **Simulate相**: 各threatの`pressure_per_turn`を`roll_dice`で振り(roll log記録、D121)、閾値を跨いだstageごとに `threat_stage` イベント候補を発行。毎ターンのpressure値は `threat_pressure` イベント(gm_only)でeffectsに載せる。
- **State Manager**: `threat_pressure`/`threat_stage` イベントのeffectsから `world.threats` のpressure set diffを生成(D107: 状態変更はdiffのみ)。`state/diff.py` がworld targetのlist要素パスを未対応なら拡張。
- **各stageは一度だけ発火**(pressureが下がらない限り)。visibilityを段階的に上げる(gm_only→scene→reader)ことで「GMだけが知る→キャラが気づく→読者に見える」の情報公開が自然に進む。
- 最終stageの`effects.encounter`は遭遇の印。scene_end連動・シーン遷移はIssue 009のスコープ。
- `threats` 未定義(default [])のプロジェクトは現行動作と完全一致。

## 完了条件

- [x] `ThreatTrack`/`ThreatStage` スキーマ(WorldState.threats、後方互換default [])
- [x] Simulate相がpressureをseeded diceで進め、閾値通過stageの `threat_stage` イベントを発行する(再発火なし、roll_ids付き)
- [x] pressure更新がState Manager経由のdiffとして適用・永続される
- [x] mist_stationに追跡者トラック(接触がおよそturn 8〜12)が入る
- [x] mock全テストpass(410)+ 実LLM 12ターン(`sandbox/issue008_llm`)で stage 25/50/75 が一度ずつ昇順発火、scene可視stageはキャラ台詞経由で物語に反映、gm_only情報のリークゼロ、roll記録完備。stage 100はダイス分散で未到達(pressure 84@12、2d6期待値通り)— encounter経路の実LLM確認は長めのランで別途

## 関連ファイル

- `src/living_narrative/agents/world_simulator.py:16` / `agents/models.py:76,84`
- `src/living_narrative/state/models.py:166,171`(WorldState)/ `state/diff.py`(world target)
- `src/living_narrative/agents/state_manager.py`(diff化)/ `agents/conflict_resolver.py:96`(candidate→Event)
- `src/living_narrative/random/engine.py:61`(roll_dice)
- `src/living_narrative/templates/mist_station/state/world.yaml`
- 評価: `docs/evaluations/2026-07-06-replay-20turn-eval.md`
