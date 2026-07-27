# 人手rubric評価 — 20260727-issue086-r4-hardening

- gate: 1.0
- result: PASS
- evaluated_at: 2026-07-27
- reviewer: Claude Fable 5による独立評価支援、ユーザー承認
- git_revision: 48f4c0e9542a09354656ecf909002216c8fa2c15
- seed: issue-085-mist-station-v1
- provider: openai-compatible
- model: cx/gpt-5.6-luna-low
- completed_turns: 30
- benchmark_json: sandbox/20260727-issue086-r4-hardening/benchmark.json
- benchmark_markdown: docs/evaluations/2026-07-27-20260727-issue086-r4-hardening-benchmark.md
- provider_failure: none

## 事前確認

- [x] 30ターン完了
- [x] JSONとMarkdownのturn番号・narrationが一致
- [x] provider failureなし
- [x] reader-visible出力に非公開情報なし
- [x] 補助artifactを確認

固定抜粋turn 1–5、13–17、26–30を全文読解し、R3、R5、R7、R8は全30ターンと
`benchmark.json`、`metrics.json`の機械証跡も確認した。

## 8項目判定

| ID | 判定 | 根拠turn / artifact | 判定理由 |
|---|---|---|---|
| R1 | YES | turn 1–5、13–17、26–30 | 地下ホームから階段、行き止まり通路への移動、足音接近から追跡者出現、窓口の音への推移が相互に矛盾しない。turn 28の「影が消えた方向」は過去の地点参照として解釈できる。 |
| R2 | YES | `mechanical.leak_scan`、抜粋15ターン | leak findingsは0で、抜粋にもGM専用情報、hidden fact、character secret、private mindの露出がない。 |
| R3 | YES | turn 7、10、13、17 | `thread_001`をturn 7でopenし、追跡者の足音停止・出現を公開eventとnarrationで描いたうえでturn 17にresolvedへ遷移した。 |
| R4 | YES | 抜粋15ターン | リナとカイの発話・行動が名前と役割で一意に識別でき、子どもと追跡者も混同されない。 |
| R5 | YES | 全30ターン、特にturn 4–7、8–10、13–16、22–24 | 待機、警戒、合図の類似表現は多いが、同義内容が新情報なしに3ターン連続する区間はない。各候補区間には案内板、水滴、scene遷移、threat進行、追跡者出現、実移動、窓口の音停止、風向きによる抜け道方針のいずれかが加わる。 |
| R6 | YES | turn 1–5、13–17、26–30、`mechanical.metrics.emotions` | 未知の子どもと足音への警戒・好奇、追跡者出現後の恐怖と脱出集中、終盤の慎重な前進が公開状況と整合し、根拠のない感情反転がない。 |
| R7 | YES | turn 1、7、10、13、17、21、25、29、`mechanical.slo.items.game` | encounter、threat stage、accepted action outcome、quest advance、rollがartifactに記録され、game実測15で要件1以上を満たす。 |
| R8 | YES | `mechanical.resume`、turn 15–16、`mechanical.metrics.replay` | turn 1–15と16–30を別プロセスで実行し、turn 16以降もapplied。resume PASS、replay match 1.0。 |

## 判断上の注記

R5が最も不確実な項目である。回転する背景eventや微小な戦術差分を新情報と認めない厳格解釈では
品質懸念が残り得るが、正本rubricの「3ターン連続で物語上の新情報なし」という条件に照らすと、
各候補区間には少なくとも一つの明示的な新情報または状態進展がある。Claude Fable 5はYESを推奨し、
ユーザーがこの判定に同意した。

`thread_002`以降には回答内容が薄いままstatus上resolvedとなる例があり、R3の成立を覆さないものの、
将来の品質改善候補として残る。

## 結論

- failed_items: none
- rerun_required: NO
- notes: 機械SLOと人手rubric R1–R8がすべてPASS。R4受入を完了する。
