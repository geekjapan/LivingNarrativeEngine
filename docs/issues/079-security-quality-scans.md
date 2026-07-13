---
id: 079
title: pip-auditとcoverage report-onlyをCIへ追加する
status: done
created: 2026-07-13
type: implementation
priority: P1
parent: 059
blocked_by: []
---

# 079: pip-auditとcoverage report-onlyをCIへ追加する

Issue 059の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- pip-audit: PRでadvisory、release時blocking。
- coverage report-only(閾値gateなし)を追加する。

## 関連ファイル

- `.github/workflows/ci.yml`
- `docs/adr/0011-release-engineering-baseline.md`
