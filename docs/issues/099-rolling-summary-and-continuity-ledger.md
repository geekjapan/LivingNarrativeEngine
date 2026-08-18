---
id: 099
title: Rolling SummaryとContinuity Ledger
status: completed
completed: 2026-08-18
created: 2026-08-18
---

# Rolling SummaryとContinuity Ledger

## 背景

20章以上の制作では、過去本文全体を次章promptへ渡せない。accepted chapterから読者可視の継続性digestを蓄積し、thread、人物arc、未回収義務を構造化して次章のcontextとsemantic reviewへ渡す必要がある。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| accepted chapterからreader-safeなrolling summaryを原子的に記録できる | state/persistence test |
| threadとcharacter arcの継続性ledgerをBook Stateに保持する | schema・StateDiff test |
| `ChapterContext`は必要なdigestだけを上限付きで投影する | context projection test |
| 未解決必須threadと既知の矛盾をsemantic reviewがblock findingにできる | semantic integration test |
| reader projectionにgm_only/private情報を含めない | disclosure regression test |
| chapter 20相当のdigestで既定上限を超えない | deterministic long-context test |

## 関連ファイル

- `src/living_narrative/book/continuity.py`
- `src/living_narrative/book/chapters.py`
- `src/living_narrative/book/coordinator.py`
- `src/living_narrative/state/models.py`
- `tests/book/test_continuity.py`

## 実装結果

accepted chapter本文からreader-safeかつ上限付きのdigestを導出し、`BookLedgerState.continuity`へStateDiff経由で永続化する。次章のdraft promptとsemantic reviewはこのdigestを入力に含め、未被覆required threadをopen ledgerとして追跡する。focused回帰と全回帰で検証済み。

## 非対象

LLMによる全本文要約の自動生成は扱わない。summaryテキストは明示入力またはdeterministicなaccepted artifact投影から生成し、外部モデル使用は別途予算統治の対象とする。
