---
id: 028-029
title: TRPGリプレイexporter強化 + character arc / 伏線レポート(DAGノード028+029統合)
status: done
created: 2026-07-07
---

# 028+029: TRPGリプレイ強化 + arc/伏線レポート

## 背景

DAG Track C残り(030 revision passを除く)。028と029は同じ `export_replay/` 面・同じデータ源(ターンartifacts+state)のため1ユニットで実装。

- **028**: 既存 `export replay` は narration連結のみ。TRPGリプレイとしては rolls(ダイス)・介入・GM注記が欲しい(Phase 6「TRPGリプレイ風出力ができる」)
- **029**: 感情推移・関係推移・スレッド開閉の一覧(Phase 6「伏線・キャラクター変化の一覧が出せる」)。019 metricsと026 reconstructionが素材を持っている

## 設計

**028 `export replay --trpg`**(既存replayの拡張フラグ or 新フォーマット、既存流儀に合わせる):
1. ターンごとに: narration本文 + ロール欄(rolls.yamlから notation/結果/label、GM卓の「ダイス目」風)+ 介入欄(interventionあれば「GM: …」)+ シーン見出し(026のシーン境界で区切り)
2. visibility規則は既存replay準拠(reader可視、D120除外)。ロールはgm情報だが**TRPGリプレイの様式として開示**(--trpgはGM向け出力と明記、reader版と分ける)

**029 `export arcs`**:
3. `export_replay/arcs.py`: metrics(019)の感情軌跡再構成を再利用し、キャラごとの感情推移表(ターン×感情、値変化のあったターンのみ)+ 関係値推移(relationship deltaの時系列)+ スレッド一覧(opened_turn/advance回数/解決 or 放置ターン数)+ memory summary一覧
4. 出力: `arcs.md`(人間可読の表)+ `arcs.yaml`。GM向け(感情・関係はcharacter可視情報のため)

## 完了条件

- [x] --trpg: mockランで rolls・介入・シーン見出しが織り込まれたreplayが出る(テスト)
- [x] arcs: 感情推移・関係推移・スレッド表がmockデータの手計算と一致(テスト)
- [x] 両方: 既存replay(reader版)の出力が不変(回帰)
- [x] mock全テストpass(658+)
- [x] 実データ確認: bench20_llmで両export。TRPGリプレイ=ロール欄(notation→結果)+シーン見出し+GM出力ヘッダ、arcs=感情変化点時系列・関係推移・スレッド表。目視妥当

## 関連ファイル

- `src/living_narrative/export_replay/`(replay/reconstruction/outline基盤)/ `cli/export.py`
- `src/living_narrative/session/metrics.py`(感情軌跡ロジック再利用)
- DAG: `docs/plan/feature-dag.md`
