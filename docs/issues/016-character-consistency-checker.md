---
id: 016
title: character consistency checker(キャラが「知らないはずのこと」を話す・秘密を漏らすの検知)
status: done
created: 2026-07-07
---

# 016: character consistency checker

## 背景

DAG Track A(並列可ノード)。Phase 5機能。leak checkerは「読者への未開示情報リーク」を見るが、「キャラクター自身の一貫性」— 知らないはずの事実への言及、自分の秘密の不用意な開示 — を見るcheckerが無い。プロンプト(情報スコープ厳守・secretsを明かさない)頼みで、破られても検知されない。

## 設計

ルールベースから開始(LLM judgeは将来拡張、コスト増のため今回見送り):

1. `character_consistency_checker`(safety/、registry登録。speech_check.pyと同型のイベント走査):
   - 対象: `character_dialogue` / `character_action` イベント(effects.character_idで話者特定)
   - **know違反**: 話者の `knowledge.does_not_know`(スキーマ確認要 — CharacterKnowledge)の各項目がイベントtextに部分一致 → `Finding(severity="warn", checker="character_consistency_check")`
   - **秘密開示**: 話者自身の `secrets` 項目がreader可視イベントのtextに部分一致 → warn(visibility=character/gm_onlyのイベントは対象外 — 内心で秘密に触れるのは正常)
   - 日本語部分一致の限界(過検知)を許容し、warnに留める(auto-apply非停止)
2. mist_stationのdoes_not_know/secretsが実際に文字列一致で機能する形か確認、必要なら項目を検知可能な表現に調整(テンプレート側)

## 完了条件

- [x] know違反warn(does_not_know項目のdialogue/action混入)、話者以外の知識は対象外
- [x] 秘密開示warn(reader可視のみ)、character/gm_only可視イベントは無視
- [x] 非該当で沈黙、auto-apply非停止(warn)
- [x] mock全テストpass(568+)(579 pass、ruff clean)
- [ ] 実LLM確認は次回の総合ランに相乗り(専用ラン不要 — checkerは非ブロッキング)— 今回は未実施、次の統合実LLMランに持ち越し

## 関連ファイル

- `src/living_narrative/safety/`(speech_check.py同型、registry登録)
- `src/living_narrative/state/models.py`(CharacterKnowledge/secrets)
- `src/living_narrative/templates/mist_station/state/characters/*.yaml`
- DAG: `docs/plan/feature-dag.md`
