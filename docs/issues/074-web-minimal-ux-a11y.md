---
id: 074
title: page.pyへ最小UX/a11yパッチを当てる
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 058
blocked_by: [064]
---

# 074: page.pyへ最小UX/a11yパッチを当てる

Issue 058の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- 空状態に`living-narrative init`案内、全input可視ラベル/aria-label、`#status`にaria-live、
  export/backupのCLI導線テキストを追加する(page.py追記のみ、rewriteなし)。
- コントラスト実測し4.5:1未満があれば調整する。
- 回帰test 1本を含む。

## 関連ファイル

- `src/living_narrative/web/page.py`
- `tests/web/`
