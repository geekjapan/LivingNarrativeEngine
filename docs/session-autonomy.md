# Session Autonomy

## User Mode Matrix

| user_mode | interventions | review | gm_vault |
|---|---|---|---|
| watcher | none | n/a | hidden |
| assistant_gm | scene_directive, character_directive, world_directive, pacing_control, tone_control, reveal_control, stop_condition | required on stop | visible |
| full_gm | assistant_gm plus event_injection, probability_bias, hidden_truth_edit, canon_edit, dice_roll_request, scene_pivot, relationship_edit, memory_edit | required by autonomy | visible |
| author | scene_directive, tone_control, pacing_control, stop_condition | required | hidden |
| player_character | bound character_directive, stop_condition | required | hidden |
| god | all interventions | bypassed, but logged | visible |

## Stop Condition Matrix

| autonomy_level | stopping behavior |
|---|---|
| manual | stops every turn |
| assist | stops on all enabled conditions |
| auto | stops on all enabled conditions or target turn count |
| watch | stops only on checker_error, scene_end, target_turn_count_reached, stop_condition |
| god | stops only on checker_error, scene_end, target_turn_count_reached, stop_condition |

`stop_condition` is always enabled and cannot be disabled in `project.yaml`.

## CLI TODO

TODO(cli capability): document concrete `resume`, `rerun_turn --replay-same-seed`, and auto-loop examples once command names are finalized.
