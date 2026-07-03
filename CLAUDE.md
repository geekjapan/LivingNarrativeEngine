# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

No source code exists yet — there is no `pyproject.toml`, `src/`, or `tests/` directory. The repository is currently a fully spec'd-out, pre-implementation project driven by **OpenSpec**. Before writing or editing any code, read (in this order):

1. `docs/project_plan.md` — the product vision/pitch ("企画書"). Motivational, not normative; long (3000+ lines, numbered `# N.` sections).
2. `docs/spec-foundation.md` — the **normative** shared contract for the whole first implementation batch (tech stack, ID conventions, information-scope model, data model shapes, turn-pipeline phases, decision log D101–D109). If anything conflicts with `project_plan.md`, `spec-foundation.md` wins.
3. `openspec/changes/<name>/proposal.md` + `specs/` + `design.md` + `tasks.md` — per-capability requirements. Not every change is fully drafted yet (see below).

**`AGENTS.md` is stale**: it describes a generic JS/TS project (camelCase, `npm test`, `src/`+`tests/`+`assets/`). The actual confirmed stack (locked in `spec-foundation.md` §2 and decision log D101–D109) is **Python 3.12+**, not JS/TS. Follow `spec-foundation.md` for stack/conventions, not `AGENTS.md`, whenever they disagree. `AGENTS.md`'s generic advice (shallow module paths, test-per-behavior, imperative commit subjects, no speculative scaffolding) still applies.

### OpenSpec change status (`openspec/changes/`)

Dependency DAG (spec-foundation §1.2), each change gates the next:

```
add-project-foundation → add-state-model → {add-random-engine, add-llm-provider}
  → add-turn-pipeline → add-agent-runtime → add-intervention → add-session-autonomy
  → add-cli-and-sample
```

All 9 changes are fully drafted (proposal + specs + design + tasks) and pass `openspec validate --all`. Check `openspec list` for live task status.

None of these have been archived into `openspec/specs/` yet (that directory doesn't exist) — nothing has landed as an applied main spec, and no code has been written against any of them. When a change's implementation is actually merged, run `/opsx:archive <change-name>` (or `/opsx:bulk-archive` for several) to fold it into the main spec.

## Commands

None yet — there is no `pyproject.toml`. Once `add-project-foundation` is implemented, expect (per `spec-foundation.md` §2 and its design doc):

```bash
uv sync                 # install deps (pytest, ruff as dev extras)
uv run pytest           # run tests
uv run ruff check .     # lint
uv run ruff format .    # format
uv run living-narrative init ...   # typer CLI entry point (later changes add turn/auto/review/status/export)
```

Do not invent or assume any of these exist until `pyproject.toml` is actually committed — verify first.

## Architecture (as specified, not yet built)

The engine is **state-first, not text-first**: the source of truth is a set of YAML state files + an append-only event/intervention/roll/diff log, not prose. Prose (`narration.md`) is a derived, regenerable view.

### Planned layout (`docs/project_plan.md` §18.3)

```
src/living_narrative/
  core/       session.py, turn.py, orchestrator.py       # turn pipeline driver
  state/      models.py, store.py, diff.py, validation.py # Pydantic v2 state schemas + StateDiff
  agents/     world_simulator.py, character.py, conflict_resolver.py,
              narrator.py, checker.py, state_manager.py
  llm/        client.py, providers.py, mock.py, schemas.py
  random/     engine.py, dice.py, tables.py
  renderers/  novel.py, replay.py, game_log.py            # novel/log output styles
  exporters/  markdown.py                                  # replay.md (novel outline etc. are later phases)
  safety/     leak_check.py, continuity_check.py
  web/        (not built in the first batch — CLI only, D101)
examples/mist_station/   # sample world used by the 10-turn smoke test
```

### Capability map (spec-foundation §1.1) → change that introduces it

| capability | responsibility |
|---|---|
| `project-workspace` | `project.yaml` schema, workspace layout, `init`/load (add-project-foundation) |
| `state-model` | all state schemas, `Visibility`, `StateDiff` apply/rollback (add-state-model) |
| `random-engine` | seeded RNG, dice notation, probability checks, weighted tables, roll log (add-random-engine) |
| `llm-provider` | provider protocol, mock + OpenAI-compatible provider, structured output validation (add-llm-provider) |
| `turn-pipeline` / `narration` | 8-phase turn driver, turn artifacts, novel/log renderer (add-turn-pipeline) |
| `agent-runtime` / `consistency-checks` | Context Builder, Character Agent, World Simulator, Conflict Resolver, State Manager, Leak/Continuity checkers (add-agent-runtime) |
| `intervention` | structured intervention schema, interpreter, visibility, history (add-intervention) |
| `session-autonomy` | user mode, autonomy level, stop conditions, GM review gate, resume (add-session-autonomy) |
| `cli` / `export-replay` | `living-narrative` CLI, sample world, replay export (add-cli-and-sample) |

Non-goals for the whole first batch (spec-foundation §1.3): web UI, SQLite/DB, image/audio generation, novel-outline export (replay export only), TRPG/RPG rules, multi-user, memory-summary/foreshadowing ledger, branch/rollback UI.

### The information-scope model (spec-foundation §4 — the most load-bearing contract)

Agents are never given omniscience. Every fact/event/intervention carries a `visibility`: `gm_only | canon | character (+known_by) | scene | reader`.

- Character Agent context = only that character's own state/knowledge + scenes they're in + facts visible to them. Never other characters' `private_mind`, never `gm_vault`.
- Narrator context = only `reader_state` + current scene's `reader_visible_facts` + this turn's reader-visible events. Never `gm_vault`/`hidden_facts`/others' secrets.
- World Simulator / State Manager can see everything but must tag every output with a visibility.
- The Leak Checker diffs narration output against `reader_state` to catch undisclosed-info leaks — this is why any future "sample world" fixture must include deliberately hidden facts (gm_vault truths, character secrets) to exercise it meaningfully.

### Turn pipeline (spec-foundation §6): 8 phases, one turn artifact dir each

`Load → Intervene → Simulate → Act → Resolve → Narrate → Check → Commit`, persisted under `workspace/runs/turn_NNNN/` (`intervention.yaml`, `agent_io/`, `events.yaml`, `rolls.yaml`, `narration.md`, `checks.yaml`, `state_diff.yaml`, `meta.yaml`). Artifacts are saved even on failure (partial artifact, never silently swallowed). Turn status: `applied | pending_review | stopped_for_review | failed`.

### State changes always go through a diff

Direct state mutation is forbidden, including in "God Mode" — every change is a `StateDiff` (`add|remove|set|delta`, dot-path, visibility, `source_event`), applied atomically per turn, reject leaves state unchanged, partial apply is a subset of changes, and an inverse diff is stored for rollback (spec-foundation §5.1).

### Key locked decisions (spec-foundation §9, D101–D109)

CLI-only in batch 1, no web UI (D101); `typer` for the CLI (D102); YAML files are the source of truth, no DB (D103); `openai` SDK + configurable `base_url` for OpenAI-compatible/Ollama/LM Studio, LiteLLM rejected as unneeded (D104); Pydantic v2 is the single schema source of truth (D105); narrative content is Japanese-first, code/identifiers are English (D106); all state mutation goes through diffs, no exceptions (D107); extension points are `Protocol` + a plain registry dict, no plugin loader yet (D108); `unresolved_threads`/branching get a data format now, no runtime behavior until Phase 5 (D109).

### Naming/ID conventions (spec-foundation §3)

IDs are `<type>_<zero-padded-number>` (`char_001`, `event_0001`, `diff_0001`, `turn_0001`). Turn numbers are 1-based. `diff`/`event`/`roll`/`intervention` IDs are unique per-project across turns. Capability and doc filenames are kebab-case; YAML keys are snake_case; Python follows PEP 8.
