---
id: 065
title: mutation APIにOrigin検証を追加する
status: open
created: 2026-07-13
type: implementation
priority: P0
parent: 054
blocked_by: []
---

# 065: mutation APIにOrigin検証を追加する

Issue 054の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- 全POST/PUT routeで`Origin`ヘッダが`http://127.0.0.1:{port}`または不在の場合のみ許可、他は403。
- 非ブラウザclient(CLI/curl、Originなし)が既存どおり動作する回帰testを含む。
- 越境Origin付きリクエストが403になるtestを追加する。

## 関連ファイル

- `src/living_narrative/web/app.py`
- `tests/web/`
- `docs/adr/0007-web-ui-security-floor.md`
