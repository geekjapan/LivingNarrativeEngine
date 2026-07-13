# Session Autonomy

> **Current implementation (2026-07-13)**: `session-autonomy`は現行の自律進行・停止条件・
> user mode契約を記述する。`turn`/`auto`は既存workspaceを読み込み、未解決のreview対象が
> ある場合は先に`review`を要求する。

## User Mode Matrix

| user_mode | interventions | review | gm_vault |
|---|---|---|---|
| watcher | none | n/a | hidden |
| assistant_gm | scene_directive, character_directive, world_directive, pacing_control, tone_control, reveal_control, stop_condition | required on stop | visible |
| full_gm | assistant_gm plus event_injection, probability_bias, hidden_truth_edit, canon_edit, dice_roll_request, scene_pivot, relationship_edit, memory_edit | required by autonomy | visible |
| author | scene_directive, tone_control, pacing_control, stop_condition | required | hidden |
| player_character | bound character_directive, dice_roll_request, stop_condition | required | hidden |
| god | all interventions | bypassed, but logged | visible |

## Stop Condition Matrix

| autonomy_level | stopping behavior |
|---|---|
| manual | stops when an enabled condition matches |
| assist | stops when an enabled condition matches |
| auto | stops when an enabled condition matches; `auto --turns N` also ends after N turns |
| watch | stops only on checker_error, scene_end, or stop_condition |
| god | stops only on checker_error, scene_end, or stop_condition |

`stop_condition` is always enabled and cannot be disabled in `project.yaml`.

The CLI `turn`/`auto` path uses auto-commit when no stop condition or checker error matches;
`autonomy_level` controls which matched conditions become `stopped_for_review`. The `--turns N`
limit ends the auto loop after N applied turns and is not written as a `target_turn_count_reached`
stop-condition artifact.

## CLI

`resume`という独立したサブコマンドはなく、既存projectを`turn`または`auto`で実行すると
次のターンから再開する。

```bash
uv run living-narrative turn \
  --project projects/mist_station/project.yaml

uv run living-narrative auto \
  --project projects/mist_station/project.yaml \
  --turns 5

uv run living-narrative auto \
  --project projects/mist_station/project.yaml \
  --until scene_end
```

review待ち（`pending_review`/`stopped_for_review`）のターンは、`review`で判断してから再開
する。`rerun_turn`は対象ターンのartifactを退避して再実行し、`--replay-same-seed`を付けると
元ターンと同じRNG位置から再現する。`failed`ターンは次の`turn`/`auto`実行で再試行される。

```bash
uv run living-narrative review \
  --project projects/mist_station/project.yaml \
  --decision rerun_turn \
  --replay-same-seed
```
