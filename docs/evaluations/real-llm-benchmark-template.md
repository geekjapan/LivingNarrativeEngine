# 実LLM benchmark転記 — <run-id>

- gate: `beta | 1.0`
- result: `PASS | FAIL`
- started_at: <ISO-8601>
- finished_at: <ISO-8601>
- git_revision: <commit>
- sample: <sample>
- seed: <random_seed>
- provider: <provider>
- model: <model>
- completed_turns: <N> / 30
- benchmark_json: sandbox/<run-id>/benchmark.json
- provider_failure: none | turn <N>: <short reason>
- resume: turn 15 → turn 16 | FAIL: <reason>

## 事前確認

- [ ] `run.status`が`PASS`
- [ ] 30ターンが`applied`
- [ ] JSONとMarkdownのturn番号・narrationが一致
- [ ] provider failureなし
- [ ] reader-visible出力に非公開情報なし
- [ ] `mechanical.metrics`、leak scan、resumeを確認

## Turns

以下のブロックをTurn 01からTurn 30まで、JSONの`turns[]`と同じ順序で繰り返す。
`reader-visible events`と`reader-visible state/delta`以外のstate、prompt、agent inputは転記しない。

## Turn <NN>

### Status

`applied` | `pending_review` | `stopped_for_review` | `failed`

### Narration

<JSONのturns[].narration。失敗してnarrationがない場合は「なし」>

### Reader-visible events

```json
[]
```

### Reader-visible state/delta

```json
{}
```

### Failure

`none` | `provider: <short reason>` | `runtime: <short reason>`

## 機械証跡

- metrics_json: sandbox/<run-id>/metrics.json
- leak_scan: PASS | FAIL — <短い根拠>
- resume: PASS | FAIL — checkpoint turn <N>, resumed turn <N>
- provider_failures: none | <turn番号と短い理由>

## 結論

- failed_items: <none or IDs>
- rerun_required: YES | NO
- notes: <秘密を含めない再現・評価メモ>
