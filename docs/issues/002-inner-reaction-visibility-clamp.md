---
id: 002
title: inner_reactionのvisibilityをCHARACTERにクランプ(内心の読者流出バグ)
status: done
created: 2026-07-06
---

# 002: 内心visibilityクランプ

## 背景

ターン1実走で、char_002 のネタバレ内心(「まさかミラが…？」)がそのまま読者ナレーションに流出した。原因(deep-reasoner診断 所見#3、**実バグ**):

- `agents/models.py:29` — `ActionCandidate.visibility` のデフォルトが `READER`
- `agents/character.py:47-58` — LLMが返した `candidate.visibility` を無検証で信用

リークチェッカーは既存秘密(gm_vault等)しか照合しないため、新規生成コンテンツのreaderタグは素通しになる(所見#4、別Issue)。

## 完了条件

- [x] マッピングループで `kind == "inner_reaction"` を `Visibility.CHARACTER` にクランプ(介入で明示的に開示された場合を除く)
- [x] `ActionCandidate.visibility` のスキーマデフォルトを `READER` から変更
- [x] プロンプト側でもvisibility規則を明記(Issue 001と連携)
- [x] 回帰テスト: LLMが inner_reaction に `reader` を返してもcharacterスコープに落ちること
- [x] mist_run_001 実走で内心が narration.md に出ないことを確認

## 関連ファイル

- `src/living_narrative/agents/models.py:27-31`
- `src/living_narrative/agents/character.py:47-58`
- 関連Issue: [001](001-character-prompt-rewrite.md), [004](004-leak-check-generated-content.md)(本Issueのタグ正常化が前提)

## 完了メモ (2026-07-06)

クランプはマッピングループではなく **スキーマ層**(`ActionCandidate` の `model_validator`)に実装 — gateway経由の全経路をカバーし、D105(スキーマ単一真実源)に沿う。`visibility` デフォルトは `READER` から `None` に変更し、validatorが kind別に解決(inner_reaction→CHARACTER固定・GM_ONLYのみ許容、action/dialogue→READER)。回帰テスト3件追加。mist_run_001 turn 2 実走: 内心2件とも `character` タグ、narration.md 流出ゼロ。
