# Issue 095: Chapter production coordinator

## 目的

BookPlanで承認した章を、候補生成、review、改稿、acceptまで原子的に追跡できるようにする。本文候補とreviewはBookLedgerのlifecycle更新と同じtransaction境界で保存し、crash recoveryと明示的なhuman decisionを維持する。

## 実装

`living_narrative.book.coordinator` に以下を追加した。

| 操作 | lifecycle | durableな副作用 |
| --- | --- | --- |
| `start_chapter_production` | `planned → running` | active chapterを設定 |
| `record_chapter_candidate` | `running/revising → candidate` | candidate/review/provenanceを書込み |
| `open_chapter_review` | `candidate → review` | candidate hashに結び付くreview journal |
| `request_chapter_revision` | `review → revising` | review decisionを記録 |
| `accept_chapter_review` | `review → accepted` | accepted decisionとnext actionを記録 |

candidate本文hashをcandidate/review/revision journal keyへ含める。これにより、改稿が同一chapterの古いcompleted journalを誤って再利用せず、candidate attemptごとのrecoveryを可能にする。

## 受入条件

- [x] 状態遷移が `project_lock` と `commit_state_diff` を通る。
- [x] candidate/review artifactがcommit前に保存される。
- [x] 初稿と改稿candidateが異なるjournalを使用する。
- [x] 改稿後に `candidate → review → accepted` へ進める。
- [x] focused book suite、静的検査、全回帰を通過する。

## 次の依存Issue

Issue 096では、本文生成そのものを外部補助scriptから回復可能な `ChapterDraftRun` に移し、candidate artifactへの入力をエンジンが所有する。
