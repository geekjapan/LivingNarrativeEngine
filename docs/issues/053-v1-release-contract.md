---
id: 053
title: 1.0の利用者・配布形態・受入基準を固定する
status: in_progress
created: 2026-07-12
type: wayfinder:grilling
priority: P0
parent: 052
blocked_by: []
---

# 053: 1.0の利用者・配布形態・受入基準を固定する

## 問い

ローカル単一利用者向け1.0は誰のどの体験を保証し、uv／Docker／packageのどの配布経路を正式対応とし、どの実測条件を満たしたら出荷可能と判定するか。

## 背景

Phase 7〜9とIssue 001〜051は完了している一方、`project_plan`のα／β／1.0定義は定性的で、E9完了と1.0完成が混同されている。現状は機能豊富なpre-βであり、次の作業を選ぶために目的地を先に固定する必要がある。

## 解決条件

- primary personaと代表ユーザージャーニーを1つに絞る
- 正式対応するinstall／起動／upgrade経路を決める
- must／should／post-1.0を判定する原則を決める
- α／β／1.0を自動検証可能・人手評価可能な条件へ置換する
- trusted in-process pluginとprovider境界を1.0へ含める範囲を決める

## 関連ファイル

- `docs/project_plan.md`
- `README.md`
- `pyproject.toml`
- `docs/adr/0004-explicit-plugin-allowlist-trust-boundary.md`
