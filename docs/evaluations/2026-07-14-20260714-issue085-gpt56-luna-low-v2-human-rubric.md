# 人手rubric評価 — 20260714-issue085-gpt56-luna-low-v2

- gate: `1.0`
- result: `FAIL`
- evaluated_at: 2026-07-14T02:08:00+09:00
- reviewer: Codex
- git_revision: `c5c0fcde79f5ff65a48b1609149db0734e9242d3`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`
- model: `cx/gpt-5.6-luna-low`
- completed_turns: 30
- benchmark_json: `sandbox/20260714-issue085-gpt56-luna-low-v2/benchmark.json`
- benchmark_markdown: `docs/evaluations/2026-07-14-20260714-issue085-gpt56-luna-low-v2-benchmark.md`
- provider_failure: none

## 事前確認

- [x] 30ターン完了
- [x] JSONとMarkdownのturn番号・narrationが一致
- [x] provider failureなし
- [x] reader-visible出力に非公開情報なし
- [x] 補助artifactを確認

## 8項目判定

| ID | 判定 | 根拠turn / artifact | 判定理由 |
|---|---|---|---|
| R1 | NO | turn 23–30 | 追跡者が見据えているscene記述と、影が消えた／見失った記述が同一turn群で併存 |
| R2 | YES | checks、turn 1–5/13–17/26–30 | critical/high leak 0、読解対象にもGM専用情報なし |
| R3 | NO | metrics threads | opened 0、resolved 0で回収実績なし |
| R4 | YES | turn 1–5/13–17/26–30 | リナとカイの行動・発話者を名前と動作で識別可能 |
| R5 | NO | turn 16–22、24–30 | 「合図まで待つ／子どもを連れて階段へ」の同義反復が3ターン超連続 |
| R6 | YES | emotions、turn 1–5/13–17/26–30 | 恐怖・警戒の表現が追跡状況と継続的に整合 |
| R7 | YES | metrics game.encounter_count | encounterが30件発火 |
| R8 | YES | mechanical.resume | 別プロセスでturn 15から16へresumeし、その後30までapplied |

## 結論

- failed_items: R1, R3, R5
- rerun_required: `YES`（修正後）
- notes: provider/modelの安定性ではなく、進行停滞・thread未生成・反復が主因。
