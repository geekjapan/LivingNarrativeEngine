---
id: 054
title: Web UIとpluginを含む1.0 security floorを決定する
status: open
created: 2026-07-12
type: wayfinder:research
priority: P0
parent: 052
blocked_by: []
---

# 054: Web UIとpluginを含む1.0 security floorを決定する

## 問い

LLM・project・plugin由来の敵対文字列を扱うlocal Web UIについて、stored XSSを確実に除去し、CSP、Origin/CSRF、TrustedHost、plugin trust、secret処理のどこまでを1.0必須防御とするか。

## 背景

`src/living_narrative/web/page.py`はintervention、checker message、world／scene／thread／timeline等を未escapeのまま`innerHTML`へ挿入する箇所がある。同一originでGM read APIとmutation APIへ到達できるため、loopback限定でもrelease blockerである。PDG/taint layerは未構築で、機械的taint検査も未評価。

## 解決条件

- dynamic DOMをsafe node construction／`textContent`へ統一する契約を決める
- malicious payloadのbrowser/DOM regression方針を決める
- CSP、TrustedHost、Origin/CSRF defenseの採否とlocal-only threat modelを記録する
- trusted in-process pluginを維持する場合の責任境界と診断表示を決める
- 1.0必須、hardening、remote化時のみ必要な防御を分離する

## 関連ファイル

- `src/living_narrative/web/page.py`
- `src/living_narrative/web/app.py`
- `src/living_narrative/plugins/sdk.py`
- `docs/rights-and-security.md`
- `docs/adr/0004-explicit-plugin-allowlist-trust-boundary.md`
- `tests/web/`

