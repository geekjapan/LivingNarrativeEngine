---
id: 078
title: packaging+clean-install acceptance(wheel/Docker/backup-restore/migration harness)を実装する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 059
blocked_by: [080]
---

# 078: packaging+clean-install acceptance(wheel/Docker/backup-restore/migration harness)を実装する

Issue 059の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- wheel build→fresh venv install→CLI起動smoke、Docker `compose build→run init→up→curl→down` smokeをCIへ追加。
- backup→改変→restore一致smokeを追加。
- βschema fixture(`beta-schema-v1` tagへpin)のload/migration regression harnessを追加。

## 関連ファイル

- `.github/workflows/ci.yml`、`Dockerfile`、`compose.yml`
- `src/living_narrative/workspace/migrations.py`
- `docs/adr/0011-release-engineering-baseline.md`
