---
id: 075
title: disclosure leak-scanを全reader可視エンドポイントへ横展開する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 058
blocked_by: [065]
---

# 075: disclosure leak-scanを全reader可視エンドポイントへ横展開する

Issue 058の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- `/status`・`/narration`・`/turns`等reader可視応答全件にgm_vault/hidden_facts/secrets/private_mindの
  leak 0件を機械検証するtestを追加する(063の検査の横展開)。
- player_character modeでsensitive/gm routeが全て403になる網羅testを含む。

## 関連ファイル

- `tests/web/`
- `src/living_narrative/web/app.py`
