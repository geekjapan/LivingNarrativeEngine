---
id: 082
title: 文書再同期P0/P1束: web→serve修正+README導線+spec-foundation現行化+issue整合
status: done
created: 2026-07-13
type: implementation
priority: P1
parent: 056
blocked_by: []
---

# 082: 文書再同期P0/P1束: web→serve修正+README導線+spec-foundation現行化+issue整合

Issue 056の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- [x] project_plan §29.6の`living-narrative web`を`serve`へ修正(P0)。
- [x] READMEへ`metrics/rollback/branch/backup/restore`+export全サブコマンドの導線を追加。
- [x] spec-foundation §3-§8を「現行契約」と明示し、§1.3/§2/§5(149)/§9 D101,D108,D109/§10へhistorical注記。
- [x] issue 038のstatus/body整合(done+実LLM gap注記→057所管)、016へ057所管注記。

## 検証記録

- `NO_COLOR=1 uv run pytest` → `900 passed, 10 skipped`
- `uv run ruff check .` → pass
- `uv run ruff format --check .` → pass
- `git diff --check` → pass

## 関連ファイル

- `docs/project_plan.md`、`README.md`、`docs/spec-foundation.md`
- `docs/issues/038-trpg-session-e7-gate.md`、`docs/issues/016-character-consistency-checker.md`
