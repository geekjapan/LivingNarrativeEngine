# 人手rubric評価 — 20260714-issue085-mist-station-v1

- gate: `1.0`
- result: `FAIL`
- evaluated_at: 2026-07-14T01:42:50+09:00
- reviewer: Codex
- git_revision: `c5c0fcde79f5ff65a48b1609149db0734e9242d3`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`
- model: `auto/best-coding`
- completed_turns: 7 / 30
- benchmark_json: `sandbox/20260714-issue085-mist-station-v1/benchmark.json`
- benchmark_markdown: `docs/evaluations/2026-07-14-20260714-issue085-mist-station-v1-benchmark.md`
- provider_failure: turn 8 / act / `ProviderConnectionError`

## 事前確認

- [ ] 30ターン完了
- [x] JSONとMarkdownの収録済みturn番号・narrationが一致
- [ ] provider failureなし
- [x] 収録済みreader-visible出力に非公開情報なし
- [ ] 全補助artifactを確認

provider failureとturn不足により、契約どおり本文rubricの読解前にFAILとした。

## 8項目判定

| ID | 判定 | 根拠turn / artifact | 判定理由 |
|---|---|---|---|
| R1 | NO | benchmark JSON | 30ターン未完了のため未判定はNO |
| R2 | NO | partial leak scan | turn 1–7のみ確認済みで全run証跡なし |
| R3 | NO | metrics threads | resolved thread 0、かつrun未完了 |
| R4 | NO | benchmark JSON | 15ターン抜粋を構成できない |
| R5 | NO | benchmark JSON | 30ターン全体を確認できない |
| R6 | NO | benchmark JSON | 15ターン抜粋を構成できない |
| R7 | YES | metrics game.encounter_count | turn 1–7でencounter 7件発火 |
| R8 | NO | mechanical.resume | turn 15未到達でresume未実施 |

## 結論

- failed_items: R1, R2, R3, R4, R5, R6, R8
- rerun_required: `YES`
- notes: gateway復旧後、新しいrun IDで再実行する。
