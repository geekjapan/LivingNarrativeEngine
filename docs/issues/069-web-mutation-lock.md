---
id: 069
title: web/service.pyのsettings/auto-run mutationへproject lockを統合しauto_run.pyを抽出する
status: open
created: 2026-07-13
type: implementation
priority: P0
parent: 060
blocked_by: [066]
---

# 069: web/service.pyのsettings/auto-run mutationへproject lockを統合しauto_run.pyを抽出する

Issue 060の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- settings書込とauto-run coordinator(turn毎の`pipeline.run`)が`project_lock`下で実行される。
- auto-run coordinatorを`web/auto_run.py`へ抽出する(behavior-preserving)。
- auto-run中の別mutationがlock競合エラーになる統合testを1本追加する。
- GitNexus impact report確認。

## 関連ファイル

- `src/living_narrative/web/service.py`
- `src/living_narrative/state/transaction.py`
- `docs/adr/0009-v1-architecture-debt-scope.md`
