---
id: 030
title: revision pass(novel draft全体への一括推敲LLMパス — Track C最終ノード)
status: done
created: 2026-07-07
---

# 030: revision pass

## 背景

DAG Track C最終。027のnovel draftは章単位推敲のため、章間の癖(定型句の反復: 「天井の亀裂から水滴」「遠雷のような街のざわめき」等が全章に残存 — bench20実データで確認済み)と文体ゆらぎが残る。全体を見た推敲パスで一段上げる(Phase 6「revision pass」)。

## 設計

1. `export_replay/revision.py`: `revise_novel(novel_draft, gateway, profile)` — 2段:
   - **全体分析(1コール)**: 全章を入力し、反復語句リスト・文体ゆらぎ・章間矛盾を構造化出力で列挙(`RevisionNotes`)
   - **章別推敲(章ごと1コール)**: 各章+RevisionNotes+前後章の末尾/冒頭200字を入力し、指摘の解消・接続の平滑化。**新規事実の発明禁止**(027と同じ制約)、幅は「表現の調整」に限定(筋・台詞の意味を変えない)
2. CLI: `living-narrative export novel --revise`(027のnovel生成に続けて実行)or 単独 `export revise --input novel_draft.md`(既存draftへの適用)。既存流儀に合わせ選択
3. 失敗時: 章単位フォールバック(元draft章のまま)、RevisionNotes失敗なら全体スキップ(draftをそのままrevised扱いにしない — 明示エラー)
4. 出力: `novel_revised.md` + `revision_notes.yaml`(何を直したかの記録)

## 完了条件

- [x] mock LLMで2段パスが走り、novel_revised.md+revision_notes.yamlが出る(構造検証)
- [x] 章フォールバック・全体スキップのエラーパステスト
- [x] mock全テストpass(673+)
- [x] 実データ確認: bench20のdraftへ適用(全5章推敲成功・フォールバックゼロ)。定型句反復が大幅減: 「規則正しい」12→2、「水滴」6→3、「遠雷」2→1

## 関連ファイル

- `src/living_narrative/export_replay/`(novel.py基盤)/ `cli/export.py`
- DAG: `docs/plan/feature-dag.md`
