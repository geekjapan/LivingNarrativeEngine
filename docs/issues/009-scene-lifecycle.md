---
id: 009
title: シーンライフサイクルが無い(scene_endは発火せず、次のシーンを開始する機構が存在しない)
status: done
created: 2026-07-06
---

# 009: シーンライフサイクル(pendingシーン + effects駆動遷移)

## 背景

20ターン評価の構造的欠陥#2。現状:

- `SceneStatus` は `active`/`ended` の2値のみ(`state/models.py:158`)。「未開始」が表現できない。
- scene_end diffを発火させるものが実運用に存在せず、**新シーンを作成・開始する機構はコードのどこにも無い**(`SceneState(` の生成はテンプレート/テストのみ、diffでのscene追加も不可)。
- 結果、summary(007)も脅威(008)も同一シーンの中でしか動けず、物語が場面を移れない。

## 設計

**テンプレート定義シーングラフ + effects駆動遷移**。シーンの「内容」はテンプレートYAMLに事前定義し(pending)、エンジンは status 遷移と登場人物引き継ぎだけを扱う。diffによるシーン新規作成は不要になる。

1. `SceneStatus.PENDING` を追加。pendingシーンは通常のシーンファイルとして `state/scenes/` に置かれ、ロードされるが、active系の文脈(narrator/character/continuity)からは除外される(既存コードは `status == ACTIVE` フィルタ済みのため、多くは自然に除外される — 要確認)。
2. 汎用遷移: イベントの `effects.scene_transition: {"end": "<scene_id>", "start": "<scene_id>"}` をState Managerが解釈し、以下のdiffを生成:
   - end側: `scene.<id>.status = ended`(既存機構)
   - start側: `scene.<id>.status = active`
   - start側の `active_characters` が空なら、end側の `active_characters` を set diffで引き継ぐ(テンプレートが明示していればそちら優先)
3. ガード: start先が存在しない/pendingでない場合はrejected change(理由付き)。endのみ・startのみも許可(endのみ=全シーン終了は現行挙動)。
4. 発火源はデータ: 008のThreatStage.effectsにそのまま載る。mist_stationのstage 100(遭遇)に `scene_transition: {end: scene_001, start: scene_002}` を持たせる。介入(event_injection)のeffectsでもGMが強制遷移できる。
5. mist_stationに `scene_002`(追跡者との対峙、status: pending)を追加。location/mood/stakes/summary/reader_visible_facts/hidden_factsを定義、active_charactersは空(引き継ぎ)。
6. `SCENE_END` stop condition(D119)は現行のまま — 遷移ターンでautoが停止しGMレビューになるのは仕様。

## 完了条件

- [x] `SceneStatus.PENDING` 追加、pendingシーンがactive系文脈(narrator/character/continuity/_active_scene_id)に混入しない
- [x] `effects.scene_transition` からState Managerが end/start/引き継ぎ のdiffを生成し、apply/rollbackが機能する
- [x] 不正な遷移先(存在しない/pending以外へのstart)はrejectされる
- [x] mist_stationの追跡者stage 100が scene_002 への遷移を運ぶ(scene_002テンプレート込み)
- [x] mock全テストpass(425)+ 実LLM 8ターン(`sandbox/issue009_llm`、pressure初期値70)で turn 6 に遷移発生 — end/start/引き継ぎの3 diff正確、SCENE_END停止→accept_all、turn 7以降のnarration・キャラ文脈は完全にscene_002、遭遇文「霧を裂いて、追跡者が二人の前に姿を現した」、リークゼロ

## 関連ファイル

- `src/living_narrative/state/models.py:158`(SceneStatus)/ `:240`(SceneState)
- `src/living_narrative/agents/state_manager.py:248`(scene_end既存経路、_changes_for_event)
- `src/living_narrative/agents/state_manager.py:296`(_active_scene_id)/ `driver.py:64`(_active_scene_mood)
- `src/living_narrative/narration/context.py:25` / `agents/context_builder.py:28` / `agents/character.py:118`(activeフィルタ)
- `src/living_narrative/session/stop_conditions.py:114`(SCENE_END)
- `src/living_narrative/templates/mist_station/state/`(world.yaml stage 100、scenes/scene_002.yaml新規)
- 評価: `docs/evaluations/2026-07-06-replay-20turn-eval.md`
