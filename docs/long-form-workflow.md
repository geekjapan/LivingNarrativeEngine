# Long-form workflow

この文書は ADR-0014 に従い、長編小説の作者意図を `BookPlanState` として提案し、
既存の canonical state と混同せずにレビューするための最初の運用手順を示す。

## 1. Story Bible を作る

Story Bible は LLM の自由文ではなく、act と chapter の構造化された作者入力である。
chapter はどの act に属するか、読者に達成すべき goal、必要な thread、人物弧、
目標語数を必ず持つ。

```yaml
premise: 霧の駅で出会った二人が帰還経路を見つける。
audience: 長編ミステリ読者
language: ja
acts:
  - id: act_001
    promise: 閉じ込められた理由を提示する。
    chapter_ids: [chapter_001]
chapters:
  - id: chapter_001
    act_id: act_001
    planned_goal: 異常な時刻表を発見する。
    required_thread_ids: [thread_001]
    character_arc_targets:
      - character_id: char_001
        delta: 他者への不信を表明する。
    target_word_range:
      min_words: 2500
      max_words: 4500
```

`act.chapter_ids` と各 `chapter.act_id` は完全に一致しなければならない。chapter IDと
act IDはそれぞれ一意であり、空白の premise、audience、goal、promise は受け付けない。

## 2. Reviewable proposal を生成する

```bash
living-narrative book plan \
  --story-bible story-bible.yaml \
  --output proposals/book-plan.yaml
```

このコマンドは、決定的な `proposal_id`、`book_plan`、`book_ledger` を含む YAML を出力する。
**この時点で canonical state は変更されない。** proposal は人間または将来のWeb review
UIが検証するための artifact であり、LLM出力を直接 state に保存する抜け道ではない。

## 3. 承認と状態更新

承認された proposal は `proposal_to_state_diff()` によって、次の二つの明示的な変更に
変換される。

| Target | Visibility | 意味 |
|---|---|---|
| `book_plan` | `canon` | 作者意図の act/章/arc/thread/word-range 計画 |
| `book_ledger` | `gm_only` | active chapter、chapter lifecycle、next action |

以降の book coordinator は、この `StateDiff` を既存の transaction/recovery boundary 内で
commitする。`book_plan.yaml` と `book_ledger.yaml` は state hash、backup/restore、
rollback、migration の対象であり、直接編集してはならない。

## 4. 状態の役割

`BookPlanState` は作者の予定、`BookLedgerState` は章制作の運用状態、World State と
append-only event/diff は実際に起きた物語である。chapter context、chapter candidate、
quality report、manuscript は派生物であり、再生成可能な workspace artifact として扱う。
