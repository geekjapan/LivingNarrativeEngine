---
id: 003
title: LLMナレーター導入(narrate相でnarratorバインディングを解決しプロズ生成)
status: open
created: 2026-07-06
---

# 003: LLMナレーター

## 背景

現行の narrate 相は `narration/renderers.py` の機械連結レンダラーのみ(narration spec通り。第1バッチにナレーターエージェントは存在しない)。イベントテキストに無条件で `。` を付与するため `…。` `）。` の二重句読点が発生し、文体もイベントの継ぎ接ぎ。ターン1品質診断で「最大の品質キラー」(所見#1)。

さらに project.yaml の `llm_bindings: {narrator: prose}` は現在**何にも消費されない死に設定** — narrate相はllm_bindingsを読まない。

これは第1バッチ最大の機能追加であり、旧プロセスなら OpenSpec change `add-llm-narrator` 相当。ADR-0001以降はこのIssueで管理する(必要なら設計をIssue内に厚めに書く)。

## 完了条件

- [ ] narrate相が `narrator` バインディング(→ `prose` プロファイル)を解決し、LLMナレーターを呼ぶ
- [ ] ナレーターの入力は情報スコープモデル厳守: `reader_state` + 現シーンの `reader_visible_facts` + 当ターンのreader可視イベントのみ(gm_vault・hidden_facts・他者の秘密は不可)
- [ ] 読者可視イベント集合を日本語プロズに書き直す(D106)。機械連結レンダラーはフォールバック/logスタイルとして残す
- [ ] LLM失敗時の挙動を定義(D110に準拠: リトライ枯渇→turn failed か、機械連結へのフォールバックかを決めてADR化)
- [ ] `_sentence()` の二重句読点も修正(LLM化後もlogレンダラーで残るため)
- [ ] mist_run_001 実走で narration.md が読める日本語プロズになること

## 関連ファイル

- `src/living_narrative/narration/renderers.py:33-45`, `narration/context.py`
- `src/living_narrative/pipeline/driver.py:225`(narrate呼び出し)
- `openspec/specs/narration/spec.md`(凍結リファレンス — 本Issueで挙動が上書きされる)
