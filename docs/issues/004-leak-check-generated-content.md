---
id: 004
title: リークチェッカーの新規生成コンテンツ対応(characterスコープのkindが未開示でreaderに出たら検出)
status: open
created: 2026-07-06
---

# 004: 生成コンテンツのリーク検出

## 背景

`safety/leak_check.py:66-73` は**既存の**秘密(gm_vault / hidden_facts / secrets / private_mind)しか照合しない。キャラクターエージェントが新規生成したイベントを `reader` とタグ付けすれば無条件で素通しになる — ターン1で内心が流出したのに `findings: []` だった理由(所見#4)。spec準拠だが安全モデルの構造的な穴。

## 完了条件

- [ ] 新チェック: `character_inner_reaction`(および他のcharacterスコープ相当kind)が、対応する開示diff(`op: add, target: reader_state`)なしに読者ナレーションへ現れたらfindingを出す
- [ ] Issue 002(タグ正常化)完了後に着手 — クランプが先、検出は防衛第二層
- [ ] テスト: 未開示inner_reactionを含むフィクスチャでfindingが出ること/開示済みなら出ないこと

## 関連ファイル

- `src/living_narrative/safety/leak_check.py:66-73`
- 関連Issue: [002](002-inner-reaction-visibility-clamp.md)(前提)
