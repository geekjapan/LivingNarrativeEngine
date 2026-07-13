---
id: 080
title: release契約doc+CHANGELOG+release checklist+βschema凍結宣言を発行する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 059
blocked_by: [066]
---

# 080: release契約doc+CHANGELOG+release checklist+βschema凍結宣言を発行する

Issue 059の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- CHANGELOG.md(Keep a Changelog形式)とrelease checklist文書を作成する。
- SemVer保証面(ADR-0005 D3/ADR-0006)とupgrade policyを明文化する。
- βschema凍結宣言: ADR-0011へ「schema_version 1 @ commit <sha>」追記+annotated tag `beta-schema-v1`付与
  (066のmeta.yamlフィールド確定後)。

## 関連ファイル

- `CHANGELOG.md`(新規)、`docs/`
- `docs/adr/0011-release-engineering-baseline.md`
