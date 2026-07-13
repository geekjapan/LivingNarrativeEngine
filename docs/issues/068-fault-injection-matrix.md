---
id: 068
title: fault injection+multiprocessテストmatrixでtransaction契約を固定する
status: done
created: 2026-07-13
type: implementation
priority: P0
parent: 055
blocked_by: [067]
---

# 068: fault injection+multiprocessテストmatrixでtransaction契約を固定する

Issue 055の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- 書込N番目後crashの注入フックを実装し、5注入点(intent前/intent後save前/save途中/save後meta前/meta途中)で
  recovery分類が正しく落ちることをassertする。
- multiprocess同時発行(turn×turn/turn×review/turn×rollback/turn×backup)でlockが直列化し、
  state交錯・RNG二重消費・turn番号衝突が起きないことをassertする。

## 関連ファイル

- `tests/pipeline/test_failure_handling.py`
- `src/living_narrative/state/transaction.py`
- `docs/adr/0008-project-transaction-recovery.md`
