---
id: 054
title: Web UIとpluginを含む1.0 security floorを決定する
status: done
created: 2026-07-12
type: wayfinder:research
priority: P0
parent: 052
blocked_by: []
---

# 054: Web UIとpluginを含む1.0 security floorを決定する

## 問い

LLM・project・plugin由来の敵対文字列を扱うlocal Web UIについて、stored XSSを確実に除去し、CSP、Origin/CSRF、TrustedHost、plugin trust、secret処理のどこまでを1.0必須防御とするか。

## 背景

`src/living_narrative/web/page.py`はintervention、checker message、world／scene／thread／timeline等を未escapeのまま`innerHTML`へ挿入する箇所がある。同一originでGM read APIとmutation APIへ到達できるため、loopback限定でもrelease blockerである。PDG/taint layerは未構築で、機械的taint検査も未評価。

## 解決条件

- dynamic DOMをsafe node construction／`textContent`へ統一する契約を決める
- malicious payloadのbrowser/DOM regression方針を決める
- CSP、TrustedHost、Origin/CSRF defenseの採否とlocal-only threat modelを記録する
- trusted in-process pluginを維持する場合の責任境界と診断表示を決める
- 1.0必須、hardening、remote化時のみ必要な防御を分離する

## 関連ファイル

- `src/living_narrative/web/page.py`
- `src/living_narrative/web/app.py`
- `src/living_narrative/plugins/sdk.py`
- `docs/rights-and-security.md`
- `docs/adr/0004-explicit-plugin-allowlist-trust-boundary.md`
- `tests/web/`


## 決定(2026-07-13承認済)

調査による事実確認: `escapeHtml()`は存在するが適用が不均一。未escapeの主経路はGM専用面(`renderGmWorld`/`renderGmThreads`/`renderGmTimeline` — hidden_facts含む)と`renderInterventionEntry`(`page.py:251-454`)。`add_middleware`呼び出しはゼロ(CORS/TrustedHost/CSP/Origin検証すべて未実装)。loopback限定bindは実装+test済(`server.py:14`、`test_server_host.py`)。secret漏洩経路はコード上なし(APIキーはenv読みのみ、`scrub_secret`でredact済) — secret処理は達成済でmust対象外。

threat model: (i) LLM出力由来のstored XSS、(ii) 同一マシン上の悪意あるページからのloopback CSRF。remote第三者はloopback bindで到達不能=対象外。

### 決定

- (a) **dynamic DOM契約**: 新規DOM builderは導入せず、既存`escapeHtml()`をLLM/project/plugin由来値の全挿入箇所へ機械的に統一適用する。`.replace(/</g,...)`のみの簡易escape(`storyEl`、`renderGmTurnDetail`)も5文字escapeへ統一。`<pre>`内JSONは`JSON.stringify`後にescapeHtml。
- (b) **regression方針**: Python側grep guard test(`.innerHTML`右辺にescapeHtml非経由の変数展開がないことを正規表現検査)+悪意payload fixtureのJSON応答検証。Playwright等の実DOMテストは導入しない(新規ツールチェーン依存がリスクに見合わない)。
- (c) **CSP=should**(`default-src 'self'; script-src 'self' 'unsafe-inline'`ヘッダ1行、escapeの保険)。**TrustedHost=不採用**(loopback固定+Origin検証で冗長)。**Origin検証=must**: mutation API(POST/PUT)で`Origin`が`http://127.0.0.1:{port}`または不在(非ブラウザclient)以外は403。CSRFトークン/セッション管理は不採用(単一利用者localに過剰)。
- (d) **plugin**: ADR-0004(in-process・sandboxなし)を1.0で維持。有効plugin一覧の診断表示(`PluginLoadResult`をserveログ or 軽量endpointへ配線)=should。
- (e) 3分類: must=innerHTML全面escape+grep guard+Origin検証 / should=CSP、plugin診断表示 / post-1.0=TrustedHost、実DOMテスト、plugin sandbox、CSRFトークン、認証・TLS(remote化時のみ)。

### ADR候補(hard-to-reverse)

- **ADR: Web UI 1.0 security floor** — loopback-only + Origin検証 + innerHTML全面escape契約の3点を1.0 floorとし、認証/TLS/CSRFトークン/plugin sandboxを意図的スコープ外と記録。Origin不在時の許可挙動(CLI/curl直叩き許容)も固定。

### 実装Issue分割

1. page.py innerHTML全面escape統一 + grep guard test(must)
2. mutation API Origin検証(must)
3. CSPヘッダ(should)
4. plugin診断表示(should)
