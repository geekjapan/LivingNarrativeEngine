# 人手rubric評価 — 20260721-issue086-post-implementation

- gate: `1.0`
- result: `FAIL`
- evaluated_at: 2026-07-22T00:19:44+09:00
- reviewer: Codex
- git_revision: `7f62ecce83e3cc7ee5d85fb1ed1c469719f085a2`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`
- model: `cx/gpt-5.6-luna-low`
- completed_turns: 30
- benchmark_json: `sandbox/20260721-issue086-post-implementation/benchmark.json`
- benchmark_markdown: `docs/evaluations/2026-07-22-20260721-issue086-post-implementation-benchmark.md`
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
| R1 | YES | turn 1–5/13–17/26–30 | scene 1からscene 2への移動後も人物、場所、追跡者の位置関係に明確な矛盾はない |
| R2 | YES | `mechanical.leak_scan`、抜粋15ターン | critical/high leak 0、読解対象にもGM専用情報なし |
| R3 | NO | `mechanical.metrics.threads` | opened 1、resolved 0、resolved ratio 0.0でthread回収なし |
| R4 | YES | turn 1–5/13–17/26–30 | リナとカイの行動・発話者を名前と動作で識別可能 |
| R5 | NO | turn 1–13、15–30 | 「カイの合図を待つ／追跡者を警戒する／逃げ道を探す」の同義反復が3ターン超連続 |
| R6 | YES | emotions、抜粋15ターン | 恐怖・警戒の表現は追跡状況と継続的に整合し、根拠のない反転なし |
| R7 | YES | `mechanical.metrics.game` | encounter 7件、quest advance 7件をartifactで確認 |
| R8 | YES | `mechanical.resume` | 別プロセスでturn 15から16へresumeし、その後30までapplied |

## 結論

- failed_items: R3, R5
- rerun_required: `YES`（修正後）
- notes: narrator binding、30ターン完走、resume、replayは成功。作者thread chainが開始されず、pacingとthread SLOが未達。
