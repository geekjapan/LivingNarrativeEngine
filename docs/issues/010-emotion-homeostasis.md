---
id: 010
title: 感情ホメオスタシスが無い(単調増加で天井飽和、減衰・負のdelta・行動反映が欠落)
status: done
created: 2026-07-06
---

# 010: 感情ホメオスタシス(ベースライン減衰 + 負のdelta指針 + 高感情の行動支配)

## 背景

20ターン評価の構造的欠陥#3。感情は毎ターンLLMのemotion_deltasで加算されるが:

- プロンプト(`agent-runtime-character-v2`)にemotion_deltasの指針が**一切無く**、緊張下のLLMは正のdeltaしか出さない → fear/curiosityが天井(100 clamp)に張り付く(20ターンランで再現、008/009検証ランでも再現)
- 減衰・慣れ・安堵の機構が無い。飽和すると行動変化のシグナルが消える
- スキーマ上 `delta: int` は負値可、clamp 0-100も実装済み(`diff.py`)— 経路は存在し、使われていないだけ

## 設計

3点セット。すべて既存機構の上に載る:

1. **ベースライン減衰(エンジン側・決定論)**
   - `CharacterState.emotions_baseline: dict[str, Percent] = {}`(その人物の平常値。空=減衰対象外、後方互換)
   - `WorldState.emotion_decay_per_turn: int = 0`(0=off、後方互換。mist_station: 5)
   - State Managerが毎ターン、生存キャラ×baseline定義済み感情ごとに `±min(rate, |current - baseline|)` のdelta opをbaseline方向へ発行(visibility=character)。既存clamp経由で適用
2. **プロンプト指針(LLM側)** — character PROMPT_TEXTに「## 感情の更新」を追加:
   - emotion_deltasは出来事に応じて -20〜+20。**安堵・解決・空振り・休息では負のdeltaを出す**
   - 既存の感情キーのみ更新(実在しないキーはrejectされる仕様の明文化)
3. **高感情の行動支配(LLM側)** — 同プロンプトに: 感情が90以上のとき、その感情が行動を支配する(fear→逃走/回避/判断力低下、curiosity→無謀な接近等)。飽和を「シグナル消失」から「行動フェーズ転換」に変える

mist_stationの各キャラに `emotions_baseline`(初期値と同値)を設定。

## 完了条件

- [x] スキーマ2フィールド追加(後方互換default)、mist_stationにbaseline+decay設定
- [x] State Managerのbaseline減衰diffが毎ターン発行され、上下両方向に働き、min-stepで止まる(オーバーシュートなし)。decay=0/baseline未定義では現行挙動
- [x] プロンプトに感情更新指針と高感情の行動支配が入る
- [x] mock全テストpass(435)
- [x] 実LLM 10ターン(`sandbox/issue010_llm`): 感情の上下動を確認 — turn 4でfear純減(-10)、LLM自身の負delta(安堵時 -8等)がturn 4/5に出現、最高値70で飽和消滅。90以上の行動支配節はホメオスタシスが効いて未発火(到達せず)— 高圧シナリオでの確認は将来ランに委ねる

## 関連ファイル

- `src/living_narrative/state/models.py:230`(CharacterState.emotions)/ WorldState
- `src/living_narrative/agents/state_manager.py`(build_state_diff、_character_output_changes近傍)
- `src/living_narrative/agents/character.py:15`(PROMPT_TEXT)
- `src/living_narrative/state/diff.py:172`(既存clamp)
- `src/living_narrative/templates/mist_station/state/`(characters/*.yaml、world.yaml)
- 評価: `docs/evaluations/2026-07-06-replay-20turn-eval.md`
