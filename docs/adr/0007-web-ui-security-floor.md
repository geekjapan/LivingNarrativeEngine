# ADR-0007: Web UI 1.0 security floor

## Context

`web/page.py`はLLM・project・plugin由来の文字列をescape不均一のまま`innerHTML`へ挿入しており、
未escapeの主経路はGM専用面(hidden_facts含む)と介入履歴に集中する。middlewareは皆無で
Origin/CSRF検証もない。loopback限定bindは実装・test済。secret漏洩経路はない。
threat model: (i) LLM出力由来のstored XSS、(ii) 同一マシン上の悪意あるページからのloopback CSRF。
remote第三者はloopback bindで到達不能=対象外(Issue 054)。

## Decision

1.0のWeb UI security floorは次の3点とする。

1. **loopback-only bind**(既存、`server.py`のHOST固定を維持)。
2. **innerHTML全面escape契約**: LLM/project/plugin由来値のDOM挿入は既存`escapeHtml()`
   (5文字escape)を必ず経由する。新規DOM builderは導入しない。grep guard testで回帰を防ぐ。
3. **mutation API Origin検証**: POST/PUTは`Origin`が`http://127.0.0.1:{port}`または
   **不在**(CLI/curl等の非ブラウザclient)の場合のみ許可し、他は403。

CSPヘッダ(`default-src 'self'; script-src 'self' 'unsafe-inline'`)とplugin診断表示はshould。
認証・TLS・CSRFトークン・セッション管理・TrustedHost・plugin sandbox(ADR-0004維持)・
実DOM(Playwright)テストは**意図的にスコープ外**とし、remote化検討時の参照点とする。

## Consequences

- Origin不在時の許可はCLI互換のための公開契約となり、変更は非ブラウザclient全てに波及する。
- escape契約はpage.py改修全てに適用され、grep guard testが機械的に強制する。
- remote公開は本floorでは安全でない。remote化にはこのADRの改訂が前提となる。
