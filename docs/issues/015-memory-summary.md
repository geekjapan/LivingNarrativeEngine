---
id: 015
title: memory summary(長期ラン用の文脈圧縮 — 直近生イベント+要約の二層文脈)
status: done
created: 2026-07-07
---

# 015: memory summary

## 背景

DAG Track A。キャラ/ナレーター文脈の過去情報は直近5ターンの生イベント(`PAST_EVENT_TURNS=5`、event_limit 20)のみで、それより古い出来事は消える。50ターン級のセッション(Phase 5完了条件)では序盤の重要な出来事をエージェントが忘れる。

## 設計

007/014と同じ実証済みパターン(Narrate相のLLM出力 → build_diff → diff適用):

1. **スキーマ**: `MemorySummary(id, up_to_turn: int, text: str)` + bundle新collection `memory_summaries`(`state/memory_summaries.yaml`、load/save追加、default [])。diff target `memory` (COLLECTION_TARGETS、add専用)
2. **設定**: `WorldState.memory_summary_interval: int = 0`(0=off後方互換)。mist_station: 10
3. **生成**: Narrate相で `turn % interval == 0` のとき、ナレーターLLM呼び出しに `memory_summary_update` フィールドを追加要求(**追加LLMコール無し** — 既存ナレーター出力の拡張。入力payloadに「直近intervalターンのreader可視イベント+前回summary」を含め、3〜5文の通史要約を書かせる)。reader可視素材のみ → leak-safe by construction(ADR-0003と同根拠)
4. **変換**: state_managerが `memory_summary_update` を add diff化(id `memory_{turn:04d}`、up_to_turn=turn)
5. **消費**: character context と narrator context の過去情報を二層化 — 「最新summary(あれば)+直近5ターン生イベント」。summaryはreader可視由来なのでキャラに渡してもリーク無し
6. テンプレートフォールバック(非LLM)は無更新

## 完了条件

- [x] スキーマ+store load/save+diff target(apply/rollback)
- [x] intervalターンでnarrator出力に要約が乗り、diff適用でmemory_summaries.yamlが伸びる
- [x] character/narrator文脈に最新summaryが入る(interval未達・off時は現行のまま)
- [x] mock全テストpass(536+ → 556)
- [x] 実LLM 12ターン(`sandbox/issue015_llm`、interval=5): memory_0005/0010の2回生成(各5文・日本語・後者が前者を整合拡張)、gm_only語のリークゼロ、turn 6以降のnarrator/キャラ両文脈に最新summary還流、非intervalターンはnull。014回帰確認で4スレッド並行進行も観測

## 関連ファイル

- `src/living_narrative/state/models.py` / `state/store.py` / `state/diff.py`(014のthreads targetと同型)
- `src/living_narrative/narration/llm_narrator.py` / `narration/models.py` / `narration/context.py`
- `src/living_narrative/agents/state_manager.py` / `agents/context_builder.py` / `pipeline/driver.py`
- DAG: `docs/plan/feature-dag.md`
