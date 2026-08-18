---
id: 102
title: Accepted Artifact限定Manuscript Export
status: in_progress
created: 2026-08-18
---

# Accepted Artifact限定Manuscript Export

## 背景

読者向け原稿にはaccepted chapterだけを含め、candidate・revising・gm_only review情報を混在させてはならない。出力は入力attempt hash、chapter順、生成物hashを含むmanifestで再現可能にする。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| accepted lifecycleのchapterだけを章順に収集する | exporter test |
| accepted attempt pointerと本文hashをmanifestに保存する | manifest test |
| candidate/review/semantic finding/内部pathを読者原稿に含めない | disclosure test |
| 欠落または未accept chapterがある場合は明示的にfailする | incomplete book test |
| Markdown原稿とYAML manifestを原子的に生成する | persistence test |
| CLIから明示出力先を指定して再生成できる | CLI integration test |

## 関連ファイル

- `src/living_narrative/book/exporter.py`
- `src/living_narrative/book/lineage.py`
- `src/living_narrative/cli/export.py`
- `tests/book/test_exporter.py`
- `tests/cli/test_export_command.py`

## 非対象

EPUB/DOCX変換は、Markdownとmanifestの正本が安定した後のformat adapterとして扱う。
