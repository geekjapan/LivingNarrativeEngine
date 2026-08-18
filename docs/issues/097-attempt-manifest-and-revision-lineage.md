---
id: 097
title: Attempt ManifestとRevision Lineage
status: in_progress
created: 2026-08-18
---

# Attempt ManifestとRevision Lineage

## 背景

最新candidateだけを上書き保存すると、改稿の理由、入力context、quality verdict、accepted本文がいつどの試行から採用されたかを再現できない。長編原稿の採否はimmutableな試行記録を正本にし、現在のcandidate表示はその投影に限定する。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| chapterごとにattempt manifestを原子的に保存・復元できる | persistence regression test |
| 各attemptは連番、candidate hash、親attempt、review、draft runを記録する | lineage construction test |
| 改稿は親attemptを指す新しいimmutable attemptとして保存される | revision integration test |
| accept時にaccepted attempt pointerをtransaction-backedに更新する | coordinator integration test |
| 最新candidate投影を置き換えても過去attemptの本文・reviewは失われない | immutable artifact test |
| reader向けexportはaccepted attemptだけを解決可能である | exporter integration test |

## 関連ファイル

- `src/living_narrative/book/lineage.py`
- `src/living_narrative/book/artifacts.py`
- `src/living_narrative/book/coordinator.py`
- `tests/book/test_lineage.py`

## 非対象

章をまたぐcontinuity digest、費用統治、原稿フォーマット変換は後続Issueで扱う。
