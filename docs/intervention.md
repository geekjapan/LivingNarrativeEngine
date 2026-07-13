# Intervention

> **Current implementation (2026-07-13)**: この文書は現行のIntervention capabilityを記述する。
> `docs/spec-foundation.md` §4/§6を規範契約、`session-autonomy.md`を自律進行と停止条件の
> 正本として参照する。

The intervention capability turns a user's free text or structured input into typed
`Intervention` objects (`docs/spec-foundation.md` §4/§6), enforces role permission, and routes
each of the 15 types (project_plan.md §10.7) to the agent that should act on it.

## The 15 types

`living_narrative.intervention.schema.HANDLING_STATUS` maps every type to its current handling
status:

- **routed** (9): `scene_directive`, `character_directive`, `world_directive`,
  `event_injection`, `tone_control`, `reveal_control`, `dice_roll_request`, `canon_edit`,
  `hidden_truth_edit` — each has dedicated pipeline wiring (see Routing below).
- **delegated** (1): `stop_condition` — saved to `intervention.yaml` and consumed by the
  session-autonomy stop-condition evaluation (D119).
- **unhandled** (5): `probability_bias`, `pacing_control`, `scene_pivot`, `relationship_edit`,
  `memory_edit` — accepted, persisted, and surfaced to Character Agent contexts as
  `constraints`, but have no dedicated state-mutation logic yet.

## Building an Intervention

Two paths, both subject to the same permission hook, both stamping `id`/`turn`/`user_role`
from the execution context (never from caller input):

```python
from living_narrative.intervention.direct_input import build_intervention_from_direct_input
from living_narrative.intervention.permissions import PermissionRejection

outcome = build_intervention_from_direct_input(
    {
        "type": "world_directive",
        "target": {"kind": "world"},
        "content": "雨が降り始める",
        "visibility": "reader",
    },
    turn=turn,
    user_role=project.user_mode,
    allocate_id=allocate_intervention_id,
)
if isinstance(outcome, PermissionRejection):
    ...  # outcome.type / .requested_user_mode / .allowed_user_modes
```

Free text goes through the Interpreter instead, which calls llm-provider's structured output
(binding key `interpreter`) and returns one or more drafts, never silently dropping a fragment
it can't classify (it falls back to `scene_directive`):

```python
from living_narrative.intervention.interpreter import interpret_free_text

result = interpret_free_text(
    gateway, "リナにはカイの様子がおかしいことに気づかせたい。ただしカイの秘密は明かさない。",
    turn=turn, user_role=project.user_mode, allocate_id=allocate_intervention_id,
)
result.interventions          # list[Intervention]
result.rejections             # list[PermissionRejection]
result.confidence              # 0.0-1.0
result.interpretation_summary  # human-readable
```

Both paths are combined by `living_narrative.intervention.service.run_intervene_phase`, which
`TurnPipeline.run()` calls every turn via its `intervention_text=`/`intervention_drafts=`
keyword arguments.

## Permission table

`check_permission(type, user_mode, permission_table)` hardcodes only the D107/D114 universal
invariant (`canon_edit`/`hidden_truth_edit` require `full_gm`/`god`); everything else is
permissive unless a `permission_table: dict[InterventionType, frozenset[UserMode]]` is passed in
— that table's real content is `session-autonomy`'s responsibility, not this capability's.

## Routing

- `character_directive`/`scene_directive`/the 5 unhandled types reach Character Agent context
  via `intervention.router.character_directives_for` — `character_directive` only its target,
  `scene_directive` the whole scene, the rest broadcast. `stop_condition` never reaches it.
- `world_directive`/`event_injection`/`dice_roll_request` become `WorldEventCandidate`s in the
  Simulate slot (`agents/world_simulator.py`) and flow through the existing Resolve pipeline
  like any other world event.
- `tone_control` overrides the Narrator's `tone_control` string
  (`intervention.router.resolve_tone_control`); `reveal_control` additionally filters
  must-not-reveal facts out of the Narrator's context.
- `canon_edit`/`hidden_truth_edit` become a synthetic resolved `Event` (`cause="intervention:<id>"`)
  plus a `canon`/`gm_vault` state diff entry in the BuildDiff slot (`agents/state_manager.py`) —
  never a direct write (D107).
- `reveal_control`'s `reveal-now`/`must-not-reveal` marks are resolved by
  `intervention.reveal` and consumed by both the Narrator (prose-side filtering) and BuildDiff
  (Reader State promotion/blocking) — see design.md D4.

## History index

`workspace/interventions.yaml` accumulates one entry per intervention, written once a turn's
Commit phase applies (`intervention.history.build_history_entries`/`append_history`), tracing
`source_event_ids` and the turn's `diff_id`. Entries are never rewritten in place;
`mark_superseded_by_rerun` flips the superseded flag when `rerun_turn` replaces a turn artifact.
