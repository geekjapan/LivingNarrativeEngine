---
id: 067
title: startup/command時のrecovery state machineとdoctor CLIを実装する
status: open
created: 2026-07-13
type: implementation
priority: P0
parent: 055
blocked_by: [066]
---

# 067: startup/command時のrecovery state machineとdoctor CLIを実装する

Issue 055の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- mutation実行前(lock取得直後)にADR-0008の分類(meta補完/discard/quarantine/現行踏襲)を自動適用。
- quarantine時はmutationを拒否しrestore/手動repairを案内する。pre-β turnは現行block挙動を維持。
- `doctor` CLI(診断表示+quarantine解除+backup復元誘導)を追加する(should部分)。
- 各分類へ落ちるfixtureでのregression testを含む。

## 関連ファイル

- `src/living_narrative/state/transaction.py`
- `src/living_narrative/cli/`
- `src/living_narrative/pipeline/turn_numbering.py`
- `docs/adr/0008-project-transaction-recovery.md`
