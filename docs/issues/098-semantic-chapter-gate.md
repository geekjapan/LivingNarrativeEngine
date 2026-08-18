---
id: 098
title: Semantic Chapter Gate
status: done
created: 2026-08-18
---

# Semantic Chapter Gate

## 背景

決定的な本文量gateだけでは、長編計画で約束したthreadが章内で扱われたか、reader-visibleな既知事実と矛盾していないかを検知できない。semantic continuity評価は、reader-safeな章コンテキストだけを入力に、確認可能な証拠と改稿指示を保存するreview artifactである。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| semantic評価結果にthread被覆とfindingを構造化して保存できる | schemaテスト |
| 必須threadが未被覆なら、モデル評価に関係なくblock findingを追加する | deterministic regression test |
| block findingがあれば`review_chapter()`は`revise`を返す | review integration test |
| findingには証拠と具体的なrepair instructionを含める | schema・artifact test |
| semantic評価はreader-safeな`ChapterContext`のみをpromptへ渡す | prompt contract test |
| semantic gateを通らない章はaccepted lifecycleへ遷移できない | coordinator統合テスト |

## 関連ファイル

- `src/living_narrative/book/review.py`
- `src/living_narrative/book/chapters.py`
- `src/living_narrative/book/coordinator.py`
- `tests/book/test_semantic_continuity.py`

## 段階的範囲

最初の実装では必須thread被覆とblock findingを扱う。beat coverage、視点一貫性、人物声、関係性・設定・時系列の矛盾検出、評価モデルのbudget制御は後続の拡張項目とする。

## 実装状態

reader-safeなsemantic assessment、必須thread未被覆の決定的block、`review_chapter()`への統合、および非accept reviewのaccepted lifecycle遷移拒否を実装した。focused test、全回帰、sandboxのコックピット統合検証を完了した。beat coverage等の拡張品質観点は後続Issueで扱う。
