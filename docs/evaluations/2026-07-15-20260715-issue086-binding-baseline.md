# Issue 086 binding-only baseline — 20260715-issue086-binding-baseline

- result: `FAIL`
- git revision: `a14b302`
- sample: `mist_station`
- seed: `issue-085-mist-station-v1`
- provider: `openai-compatible`（local gateway）
- model: `cx/gpt-5.6-luna-low`
- bindings: `character_default`, `narrator`
- completed turns: `30 / 30`
- resume: `PASS`（turn 15 → 16、別プロセス）
- provider failure: none
- narrator mode: `llm` 29 turns / `renderer_fallback` 1 turn（turn 20、structured output不正）
- calls: character 60 / narrator 30
- source metrics: `sandbox/20260715-issue086-binding-baseline/metrics.json`

## 機械結果

| 項目 | 実測 | 判定 |
|---|---:|---|
| completed turns | 30 | PASS |
| replay match rate | 1.0 | PASS |
| max consecutive stall turns | 13 | FAIL（≤3） |
| threads opened / advanced / resolved | 1 / 9 / 0 | FAIL |
| max open turns | 29 | FAIL（≤25） |
| critical/high leak findings | 0 | PASS |
| encounter count | 30 | 反復制御前の観測値 |
| scene transitions | 1 | OBSERVED |

## 観測

characterとnarratorのbindingだけを修正しても、自由文の「階段へ進む」「壁を調べる」は
正本stateへ反映されなかった。turn 16以降もsceneは行き止まりの通路のまま、移動・退路探索の
同義反復が続いた。したがってIssue 086のAction Intent、authored Outcome、fallback、encounter
recurrence、state-first thread lifecycleの実装が必要である。
