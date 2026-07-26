# 人手rubric評価 — 20260722-issue086-fallback-fix

- gate: `1.0`
- result: `FAIL`
- evaluated_at: 2026-07-22T00:58:45+09:00
- reviewer: Codex
- git_revision: `7f62ecce83e3cc7ee5d85fb1ed1c469719f085a2` + implementation diff `fc6f460d318599d8e4b725017c2355ff2a3aacda33b3d43f5a98d86165c2803f`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`
- model: `cx/gpt-5.6-luna-low`
- completed_turns: 30
- benchmark_json: `sandbox/20260722-issue086-fallback-fix/benchmark.json`
- benchmark_markdown: `docs/evaluations/2026-07-22-20260722-issue086-fallback-fix-benchmark.md`
- provider_failure: none

## 事前確認

- [x] 30ターン完了
- [x] JSONとMarkdownのturn番号・narrationが一致
- [x] provider failureなし
- [ ] narrator fallbackなし（turn 21に`StructuredOutputError`）
- [x] reader-visible出力に非公開情報なし
- [x] 補助artifactを確認

## 8項目判定

| ID | 判定 | 根拠turn / artifact | 判定理由 |
|---|---|---|---|
| R1 | YES | turn 1–5/13–17/26–30 | scene遷移後も人物、場所、追跡者の位置関係に明確な矛盾はない |
| R2 | YES | `mechanical.leak_scan`、抜粋15ターン | critical/high leak 0、読解対象にもGM専用情報なし |
| R3 | YES | `mechanical.metrics.threads`、action outcomes | authored threadを4件resolveし、resolved ratio 0.667 |
| R4 | YES | turn 1–5/13–17/26–30 | リナとカイの行動・発話者を名前と動作で識別可能 |
| R5 | NO | turn 8–12、18–20、22–30 | 「合図まで待つ／追跡者を警戒する／水滴を数える」の同義反復が3ターン超連続 |
| R6 | YES | emotions、抜粋15ターン | 恐怖・警戒の表現は追跡状況と継続的に整合し、根拠のない反転なし |
| R7 | YES | `mechanical.metrics.game` | encounter 7件、quest advance 2件をartifactで確認 |
| R8 | YES | `mechanical.resume` | 別プロセスでturn 15から16へresumeし、その後30までapplied |

## 結論

- failed_items: R5（加えて機械gateはthread max-openとnarrator fallbackがFAIL）
- rerun_required: `YES`（修正後）
- notes: authored fallback開始とpacingは改善。emergent threadの長期未回収と、Outcomeがnarrationへ接地しない反復が残る。
