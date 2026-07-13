---
id: 084
title: web UIのDOMレベルXSS regression test(browser harness)を追加する
status: open
created: 2026-07-13
type: implementation
priority: P2
parent: 054
blocked_by: []
---

# 084: web UIのDOMレベルXSS regression test(browser harness)を追加する

PR #24のレビュー(CodeRabbit `tests/web/test_web_app.py`)からの follow-up。現行の
escaping regression testは、`innerHTML` sinkが`escapeHtml`/`*Badge` helperまたは明示
allowlistを通ることをJS source上で静的に検証し(`test_inner_html_template_values_use_escape_html`)、
hostile payloadがAPIでJSON-escapeされページ側で`escapeHtml`に渡ることを検証する
(`test_hostile_project_payload_stays_in_json_and_is_escaped_in_page`)。source levelでは
contractを担保するが、実DOM上でscript実行やevent-handler属性が挿入されないことは検証していない。

本Issueでは、Starlette `TestClient`ベースの現行web test suiteに、renderされたDOMを実際に
評価するbrowser harness(Playwright)を追加し、hostile reader/GM fixtureでのXSS非注入を
end-to-endで検証する。PR #24の correctness fixとは独立した test-infra追加のため分離した。

## 完了条件

- Playwright(Chromium)をweb test向けに配線する(`PLAYWRIGHT_BROWSERS_PATH`等の既存設定を利用)。
- hostile reader viewとGM viewのfixtureをloadし、注入された要素・`on*` event-handler属性が
  DOMに存在しないことをassertする。
- 既存のJSON payload checkは維持し、reader/GM両経路をカバーする。
- CIでbrowser harnessが安定実行できることを確認する(不安定な場合はopt-in markとして隔離)。

## 関連ファイル

- `tests/web/test_web_app.py`
- `src/living_narrative/web/page.py`
- `pyproject.toml`(Playwright依存・test配線)
