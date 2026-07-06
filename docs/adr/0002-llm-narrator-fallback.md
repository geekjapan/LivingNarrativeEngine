# ADR-0002: LLMナレーター失敗時は機械連結レンダラーへフォールバック(turn failedにしない)

- Status: accepted
- Date: 2026-07-06
- 関連: Issue 003(LLMナレーター導入)、D110(LLMリトライ枯渇→turn failed)、D106、D122

## Context

Issue 003 で narrate 相に LLM ナレーターを導入した。`project.yaml` の `llm_bindings: {narrator: <profile>}` があり、かつ renderer style が `novel` で、読者可視の素材(イベント or シーン事実)が1件以上あるときだけ LLM を呼ぶ。それ以外は従来の機械連結レンダラー。

問題は LLM 失敗時(接続リトライ3回枯渇 = `ProviderConnectionError`、構造化出力の検証失敗 = `StructuredOutputError`)の扱い。D110 に従えば turn failed だが、ナレーションは状態を生まない**派生ビュー**であり(state-first 原則: `narration.md` は再生成可能)、Simulate/Act/Resolve の結果はこの時点で確定済み。プロズ生成の失敗だけでターン全体を捨てるのは、探索用途では損失が大きい。

## Decision

ナレーター LLM の失敗は turn failed にせず、**機械連結レンダラー(novel)へフォールバックしてターンを続行**する。

- フォールバック発生は `agent_io/narrate.yaml` に `mode: renderer_fallback` + 例外種別/メッセージとして必ず記録する(黙って劣化しない)。
- D110 は**状態を生む LLM エージェント**(Character / World Simulator / Conflict Resolver / State Manager / Checker)に引き続き適用。ナレーターだけが例外で、根拠は「出力が派生ビューであること」。
- narrate 相の成否モードは `agent_io/narrate.yaml` の `mode` フィールド(`llm | renderer | renderer_fallback`)が正。

## Consequences

- LLMゲートウェイ停止中でも auto ループが narrate で止まらない。品質は機械連結に落ちるが、`agent_io/narrate.yaml` で検出可能。
- フォールバック文面も従来どおり Check 相(leak/continuity)を通る。
- 将来「フォールバック不可・厳格モード」が欲しくなったら、project.yaml かランタイムパラメータで opt-in を追加する(現時点では作らない)。
