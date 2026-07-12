---
id: 058
title: 1.0の日常利用UXとaccessibility合格基準を決定する
status: open
created: 2026-07-12
type: wayfinder:prototype
priority: P1
parent: 052
blocked_by: [053]
---

# 058: 1.0の日常利用UXとaccessibility合格基準を決定する

## 問い

primary personaが「init→遊ぶ→介入→review→停止／再開→export→backup」を迷わず完遂できるために、CLIとWebのどのjourneyを1.0必須とし、何を観察して合否を判断するか。

## 背景

FastAPI UIと主要APIは実装済みだが、`web/page.py`は単一の大きなinline UIで、実ユーザーの日常利用評価、accessibility、error recovery、全機能discoverabilityは未証明。Web reviewの`edit`／`rerun_turn`はCLI限定である。

## 解決条件

- primary journeyと補助journeyを固定する
- task completion、誤操作、復旧、情報scope、accessibilityの観察項目を決める
- Web必須、CLI必須、片方だけでよい機能を分ける
- 3つ目の実用sampleとonboardingの必要性を評価する
- UI全面rewriteを避け、合格に必要な最小変更を切れる状態にする

## 関連ファイル

- `src/living_narrative/web/page.py`
- `src/living_narrative/web/app.py`
- `src/living_narrative/cli/`
- `README.md`
- `docs/issues/020-web-ui-skeleton.md`
- `docs/issues/025-diff-review-ui.md`

