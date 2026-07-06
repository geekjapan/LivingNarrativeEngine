---
id: 006
title: ターン間の連続性が無い(timeline未記録・過去イベント不可視・emotion_deltas未消費)
status: done
created: 2026-07-06
---

# 006: ターン間連続性

## 背景

mist_run_002(実LLM 6ターン、2026-07-06)で品質所見#1〜#5修正後の再評価を実施。地文・visibility・背景イベントは良化した一方、**全6ターンが同じ冒頭ビート(霧+規則正しい足音)を再演**し物語が進まない。診断で判明した構造的原因:

1. **timelineが常に空** — Commit相はイベントを `runs/turn_NNNN/events.yaml`(アーティファクト)にしか書かず、`state/timeline.yaml` に追記しない。6ターン後も `[]`。
2. **キャラクターが過去を見ない** — Act相の `build_character_context(events=...)` に渡るのは当ターンのSimulate出力のみ(`driver.py:185`)。turn 6でも `visible_events: []`。Context Builderの `event_limit=20` は死にパラメータ。
3. **emotion_deltas / goal_updates が未消費** — `CharacterAgentOutput` スキーマに定義はあるが消費箇所ゼロ(モデル定義のみ)。キャラの `emotions` はターン1から不変(fear:30/curiosity:60)。State Managerのdiff生成対象は death / scene_end / reveal_text / 介入編集だけ。
4. **scene summaryが静的** — シーン状況の更新経路が無い。

補足: spec-foundation §1.3 の非目標「memory-summary/foreshadowing ledger」はフル記憶機構の話。timeline追記と直近イベントの文脈供給は state-model / turn-pipeline の既存スキーマの範囲内で、非目標に抵触しない最小の連続性。

軽微な別件(このrunで観測): turn 4 のナレーションで リナ が「誰か」「その人物」と匿名化された。ナレーター文脈へのキャラクター名の渡し方に穴の可能性。要再現確認 → 別issue候補。

## 完了条件

- [x] Commit相が適用済みターンのイベントを `timeline.yaml` に追記する(既存 `TimelineEntry` スキーマ、visibility保持)
- [x] Act相の character context に直近Nターンの可視イベント(timeline由来、visibilityフィルタ済み)が入る(`PAST_EVENT_TURNS=5`)
- [x] emotion_deltas / goal_updates をState Manager経由でdiff化して適用する(clamp 0-100、visibility=character、実在しない感情キーはreject)
- [x] mist_station実LLMで6ターン回し、ビート再演が解消しキャラ感情が推移することを確認(`sandbox/issue006_llm`: fear 30→75 / curiosity 60→100(clamp)/ unease 50→85。冒頭定型文の逐語繰り返しは残るが内容は進行)

## 関連ファイル

- `src/living_narrative/pipeline/driver.py:185`(Act文脈)/ Commit相
- `src/living_narrative/agents/context_builder.py`(event_limit既存)
- `src/living_narrative/agents/state_manager.py`(diff生成)
- `src/living_narrative/agents/models.py:60`(emotion_deltas定義)
- 実測: `sandbox/mist_run_002/`(6ターン、diff全部空、timeline `[]`)
