---
id: 064
title: page.pyのinnerHTMLをescapeHtmlへ全面統一しgrep guardで固定する
status: open
created: 2026-07-13
type: implementation
priority: P0
parent: 054
blocked_by: []
---

# 064: page.pyのinnerHTMLをescapeHtmlへ全面統一しgrep guardで固定する

Issue 054の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- LLM/project/plugin由来値の`innerHTML`挿入箇所すべてが`escapeHtml()`(5文字escape)を経由する。
  対象: `renderGmWorld`/`renderGmThreads`/`renderGmTimeline`/`renderReview`/`renderInterventionEntry`/`renderGmTurnDetail`/`storyEl`。
- `.replace(/</g,...)`のみの簡易escapeを5文字escapeへ統一。`<pre>`内JSONは`JSON.stringify`後にescape。
- grep guard test(`.innerHTML`右辺のescapeHtml非経由変数展開を検出)を追加し、この変更なしで失敗する。
- 悪意payload fixture(`<img src=x onerror=...>`等)のJSON応答検証testを追加する。

## 関連ファイル

- `src/living_narrative/web/page.py`
- `tests/web/`
- `docs/adr/0007-web-ui-security-floor.md`
