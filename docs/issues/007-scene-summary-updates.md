---
id: 007
title: scene summaryが静的(更新経路が無く、ナレーションが毎ターン場面を再確立する)
status: done
created: 2026-07-06
---

# 007: scene summary更新経路

## 背景

Issue 006(ターン継続性)解決後の実LLM 6ターン(`sandbox/issue006_llm`)で、物語内容は進行する一方、冒頭のシーン設定文(霧+規則正しい足音)が毎ターン逐語で再登場する。調査で判明した構造:

1. **`SceneState` に summary フィールドが無い**(`state/models.py:240` — location/time/mood/stakes/reader_visible_facts/hidden_facts のみ)。「シーンの現在状況」を表す可変フィールドが存在しない。
2. **ナレーター文脈は静的情報のみ** — `build_narrator_context`(`narration/context.py:18`)が渡すのは `reader_state_facts` + `scene_reader_visible_facts` + 当ターンイベント。facts はシーン開始時から不変のため、ナレーターは毎ターン同じ素材から場面を再確立する。
3. **World Simulatorはルールベース**(`world_simulator.py:16`、テーブル駆動・LLM無し)なので、散文のシーン状況を書ける立場にない。

## 設計(ADR-0003に記録)

ナレーターLLM出力に `scene_summary_update`(1〜2文、シーンの現在状況)を追加し、State Managerが `set` diff(target=scene, path="summary", visibility=scene)に変換する。

- Narrate相はBuildDiff相の**前**にあるため、既存パイプライン順で自然に流せる(追加LLM呼び出しゼロ)。
- ナレーター入力はreader可視情報のみ → 生成summaryは構造的に `gm_only`/`hidden_facts` をリークできない(leak-safe by construction)。
- 次ターンでナレーター文脈とキャラクター文脈の両方が `scene.summary` を読む → 「前ターンの状況の続きから語る」が可能になる。
- テンプレートフォールバック(非LLMナレーター)は summary 更新なし(現状維持)で可。

## 完了条件

- [x] `SceneState.summary: str = ""`(後方互換デフォルト、既存YAMLはそのまま読める)
- [x] ナレーター出力スキーマに `scene_summary_update: str | None` が入り、プロンプトが更新を指示する
- [x] State Managerが summary 更新を `set` diff(visibility=scene)化し、Commit相で適用される
- [x] ナレーター文脈とキャラクター文脈に現在の `scene.summary` が入る
- [x] mist_station実LLMで6ターン回し、冒頭の場面設定文が毎ターン逐語再演されない(状況の続きから語られる)ことを確認(`sandbox/issue007_llm`: 6ターン全部でsummary set diff、逐語再演ゼロ、リークゼロ)

## 検証後の残観察(次issue候補)

逐語再演は解消したが、霧+足音の**モチーフ**は弱まりながら4/6ターンの冒頭に再登場(T3/T5は行動・台詞から開始)。完全に消すならナレータープロンプトに「scene_summaryが既に扱った環境描写を新規observationとして再導入しない」を明示する案。

## 関連ファイル

- `src/living_narrative/state/models.py:240`(SceneState)
- `src/living_narrative/narration/llm_narrator.py`(出力スキーマ・プロンプト・payload)
- `src/living_narrative/narration/context.py` / `narration/models.py`(NarratorContext)
- `src/living_narrative/agents/context_builder.py`(キャラ文脈)
- `src/living_narrative/agents/state_manager.py` / `state/diff.py`(diff化)
- `src/living_narrative/pipeline/driver.py`(Narrate→BuildDiff配線)
- 実測: `sandbox/issue006_llm/`(冒頭文の逐語繰り返し)
