---
id: 096
title: 回復可能なChapterDraftRun
status: done
created: 2026-08-18
---

# 回復可能なChapterDraftRun

## 背景

長編の本文生成では、モデル呼出しの完了後にプロセスが停止しても、同一試行を重複課金・重複生成せずに回復できなければならない。本文は候補artifactとして扱い、正本状態を直接変更しない。実行証跡はproject内の永続領域に残し、後続のreview、revision lineage、exporterが参照できるようにする。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| `request.yaml`と`prompt.yaml`をモデル呼出し前に原子的に保存する | 失敗復帰テスト |
| 本文レスポンスを`response.yaml`として保存する | 正常系テスト |
| `meta.yaml`を最後のcompletion markerとして保存する | 正常系・再開テスト |
| `response.yaml`が存在する場合、providerを再呼出しせずに再開する | provider呼出し回数を検証するテスト |
| provider失敗時にも失敗証跡を保存し、例外を呼出し元へ返す | 失敗復帰テスト |
| reader-safeな`ChapterContext`だけをpromptへ渡す | request/prompt artifactのテスト |

## 関連ファイル

- `src/living_narrative/book/drafting.py`
- `tests/book/test_drafting.py`
- `src/living_narrative/book/chapters.py`
- `src/living_narrative/book/artifacts.py`

## 非対象

本Issueではcandidateの採否、revision lineage全体、章をまたぐrolling summary、書籍exportは扱わない。これらは後続Issueで管理する。

## 実装メモ

run identityは`chapter_{chapter_id}_attempt_{attempt:03d}`とし、artifactは`workspace/runs/chapter_drafts/`配下へ置く。`meta.yaml`がなければ未完了として扱い、保存済み`response.yaml`を再利用してcompletionを確定できるようにする。

## 実装状態

focused test、静的検査、全回帰、および`transmigrated-crown` sandboxでのコックピット統合検証を完了した。
