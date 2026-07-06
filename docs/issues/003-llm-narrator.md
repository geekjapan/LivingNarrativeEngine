---
id: 003
title: LLMナレーター導入(narrate相でnarratorバインディングを解決しプロズ生成)
status: done
created: 2026-07-06
---

# 003: LLMナレーター

## 背景

現行の narrate 相は `narration/renderers.py` の機械連結レンダラーのみ(narration spec通り。第1バッチにナレーターエージェントは存在しない)。イベントテキストに無条件で `。` を付与するため `…。` `）。` の二重句読点が発生し、文体もイベントの継ぎ接ぎ。ターン1品質診断で「最大の品質キラー」(所見#1)。

さらに project.yaml の `llm_bindings: {narrator: prose}` は現在**何にも消費されない死に設定** — narrate相はllm_bindingsを読まない。

これは第1バッチ最大の機能追加であり、旧プロセスなら OpenSpec change `add-llm-narrator` 相当。ADR-0001以降はこのIssueで管理する(必要なら設計をIssue内に厚めに書く)。

## 完了条件

- [x] narrate相が `narrator` バインディング(→ `prose` プロファイル)を解決し、LLMナレーターを呼ぶ(`narration/llm_narrator.py::run_narrate_phase`)
- [x] ナレーターの入力は情報スコープモデル厳守: `reader_state` + 現シーンの `reader_visible_facts` + 当ターンのreader可視イベントのみ(入力は既存の `NarratorContext` のみ)
- [x] 読者可視イベント集合を日本語プロズに書き直す(D106)。機械連結レンダラーはフォールバック/logスタイルとして残す
- [x] LLM失敗時の挙動を定義 → ADR-0002: 機械連結novelへフォールバックし `agent_io/narrate.yaml` に `mode: renderer_fallback` を記録。turn failedにしない
- [x] `_sentence()` の二重句読点も修正(`…` `」` `）` 等の閉じ文字には `。` を付けない)
- [x] mist_run_001 実走で narration.md が読める日本語プロズになること(turn_0003, mode: llm, prose プロファイル)

## 関連ファイル

- `src/living_narrative/narration/renderers.py:33-45`, `narration/context.py`
- `src/living_narrative/pipeline/driver.py:225`(narrate呼び出し)
- `openspec/specs/narration/spec.md`(凍結リファレンス — 本Issueで挙動が上書きされる)
