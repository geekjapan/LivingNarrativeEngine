---
id: 063
title: mock providerによる代表ジャーニーE2E testをCI常設する
status: done
created: 2026-07-12
type: implementation
priority: P0
parent: 052
blocked_by: []
---

# 063: mock providerによる代表ジャーニーE2E testをCI常設する

## 問い

ADR-0005 D4のα gateを構成する「mock providerでのD1代表ジャーニーE2E自動走行」を、
どのturn数・介入種別・export検証で1本のCI常設testにするか。

## 背景

ADR-0005(Issue 053)でα gateが「全test green + mock journey E2E CI pass」と定義され、
これが1.0受入の唯一の新規実装mustとして確定した。既存はunit/integration/smokeのみで、
init→serve→Web UI経由の介入→exportを一気通貫で走るtestが無い。

## 完了条件

- clean stateから `living-narrative init`(sample world)→ serve(Web API経由)→
  介入を含む複数turn進行 → `export`(小説原案)までを1つのtestで自動走行する。
- mock providerのみを使い、決定性(seed固定)を保つ。
- 介入は最低1種(user intervention)を実際にWeb API経由で投入する。
- export成果物の存在と最低限の構造(空でない、visibility漏洩なし)を検証する。
- CIで常設実行され、失敗が1.0 gateの赤信号になる。
- turn数・介入種別・検証内容をtest内に文書化する。

## 関連ファイル

- `docs/adr/0005-v1-release-contract.md`
- `tests/smoke/`
- `src/living_narrative/cli/`
- `src/living_narrative/web/`
