# State Model

The state-model capability is the Pydantic v2 source of truth for workspace state files. It follows `docs/spec-foundation.md` for ID formats, visibility scopes, and StateDiff semantics.

## Files

- `world.yaml`: one `WorldState`.
- `factions.yaml`: optional list of `FactionState`.
- `characters/*.yaml`: one `CharacterState` per character.
- `relationships.yaml`: directed `RelationshipState` entries keyed by `from` and `to`.
- `scenes/*.yaml`: one `SceneState` per scene, with `hidden_facts` as scoped `HiddenFact` objects.
- `canon.yaml`, `reader_state.yaml`, `gm_vault.yaml`: scoped fact lists.
- `timeline.yaml`, `unresolved_threads.yaml`: turn event index and unresolved thread data.

`StateStore.load()` accepts either the state directory or a workspace directory containing `state/`. The fixed seven files from spec-foundation D117 must exist; empty fixed collection files load as empty lists.

## StateDiff

`StateDiff` applies `add`, `remove`, `set`, and `delta` changes atomically. Dot paths replace scalars directly, append/remove scalar list values, and resolve object-list removals by `id`; relationships use the special `<from_id>__<to_id>` key.

Delta changes are only valid for numeric fields. Percent fields clamp to `0..100`, and the apply report records the unclamped computed value.

## Rollback

Applying a diff returns an `InverseStateDiff`. Multiple turns roll back by applying inverse diffs in descending turn order.

JSON Schema export is available with:

```bash
living-narrative-state-schemas docs/schemas/state
```
