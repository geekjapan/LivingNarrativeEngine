---
id: 077
title: CI hardening: frozen sync+Python matrix+web-extra import guardを導入する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 059
blocked_by: []
---

# 077: CI hardening: frozen sync+Python matrix+web-extra import guardを導入する

Issue 059の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- `uv sync --frozen --extra web`化。3 job matrix(3.12+web/3.13+web/3.12 core-only)。
- web系jobでpytest前に`python -c "import fastapi, uvicorn"`を実行しskip偽装を失敗化する。
- filterwarnings整備(TestClient deprecation対応を含む)。

## 関連ファイル

- `.github/workflows/ci.yml`
- `docs/adr/0011-release-engineering-baseline.md`
