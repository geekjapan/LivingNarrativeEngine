---
id: 122
title: 20〜30章品質scale E2Eを追加する
status: completed
created: 2026-08-21
type: test
priority: P1
parent: 110
blocked_by: [119, 120, 121]
labels: [long-form, quality, e2e, export, resume]
---

# 122: 20〜30章品質scale E2Eを追加する

## 背景

単一chapterのfocused testだけでは、長編productionに必要なcontinuityの累積、phase-boundary stopからのresume、著者承認後のexportを同時に検証できない。v0.4.0では、deterministic gatewayを用いる20章fixtureでこれらの境界を一つのE2Eとして固定する。

## 完了条件

- [x] 2 act・20 chapterの固定BookPlanを用意し、各chapterをSemantic Gate経由でauthor reviewまで進めた。
- [x] 第10章でdraft後のphase-boundary stopを発生させ、providerを再実行せずreview状態までresumeすることを確認した。
- [x] 全chapterのacceptは明示的な`accept_chapter_review()`でのみ行い、auto-acceptを導入しなかった。
- [x] 20件のcontinuity entry、actごとのsummary、open threadの解消を確認した。
- [x] accepted immutable attemptだけを利用するreader-safe manuscript exportが20章分を出力することを確認した。

## 実行方法

```bash
uv run pytest tests/book/test_quality_scale_e2e.py -q
```

このfixtureは外部providerへ接続せず、公開promptを検証するdeterministic gatewayを使う。したがって品質gate、recovery、exportの回帰を短時間で再現できる。

## 非対象

数十万文字の実生成や審査員モデルによる文芸品質の採点は、v0.5.0以降のeditorial rubricおよび長期benchmarkで扱う。
