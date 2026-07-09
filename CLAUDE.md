# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

**Phase 1 batch (all 9 OpenSpec changes) is implemented, merged, and archived** (2026-07-03). The engine runs end-to-end via the `living-narrative` CLI with mock or OpenAI-compatible LLM providers. The normative docs, in reading order:

1. `docs/project_plan.md` — the product vision/pitch ("企画書"). Motivational, not normative; long (3000+ lines, numbered `# N.` sections). Roadmap for Phases 0–9 is §20; Phases 1–3 are effectively covered by the implemented batch.
2. `docs/spec-foundation.md` — the **normative** shared contract for the first implementation batch (tech stack, ID conventions, information-scope model, data model shapes, turn-pipeline phases, decision log D101–D122). If anything conflicts with `project_plan.md`, `spec-foundation.md` wins.
3. `openspec/specs/<capability>/spec.md` — the applied main specs (12 capabilities), a **frozen reference** for implemented behavior (OpenSpec is retired for new work — see below).

**`AGENTS.md` is stale**: it describes a generic JS/TS project (camelCase, `npm test`, `src/`+`tests/`+`assets/`). The actual confirmed stack (locked in `spec-foundation.md` §2 and decision log D101–D122) is **Python 3.12+**, not JS/TS. Follow `spec-foundation.md` for stack/conventions, not `AGENTS.md`, whenever they disagree. `AGENTS.md`'s generic advice (shallow module paths, test-per-behavior, imperative commit subjects, no speculative scaffolding) still applies.

### Development process

`dev-gear: G2` — lightweight Issue/ADR loop. **OpenSpec (OPSX) is retired for new work** (ADR-0001): all 9 Phase-1 changes are archived under `openspec/changes/archive/2026-07-03-*`, and `openspec/specs/` is kept as a frozen reference only. Do not create new OpenSpec changes.

New work follows this loop:

1. **Issue** — one markdown file per unit of work in `docs/issues/NNN-slug.md`: frontmatter (`id`, `title`, `status: open | in_progress | done`, `created`), then context (why), done-when criteria, and file pointers. Prose is Japanese-first; identifiers English.
2. Implement → `/verify` (and `/code-review` when warranted) → flip the issue's `status` to `done`.
3. **ADR** — any decision that would previously have been a D1xx entry goes to `docs/adr/NNNN-slug.md` (context / decision / consequences). The D101–D122 log in spec-foundation §9 remains valid and is continued by ADRs, not amended.

## Commands

```bash
uv sync                 # install deps (pytest, ruff as dev extras)
uv run pytest           # run tests (341 tests, ~2s)
uv run ruff check .     # lint
uv run ruff format .    # format
uv run living-narrative init --title T --output DIR --template mist_station  # scaffold a project
uv run living-narrative turn --project DIR/project.yaml    # run one turn (also: auto/review/status/export)
```

Local smoke runs live in `sandbox/` (gitignored). An OmniRoute gateway at `http://127.0.0.1:20128/v1` provides OpenAI-compatible models (`auto/best-coding`, `auto/best-chat`, …; no real API key needed — set `OPENAI_API_KEY` to any non-empty value).

## Architecture

The engine is **state-first, not text-first**: the source of truth is a set of YAML state files + an append-only event/intervention/roll/diff log, not prose. Prose (`narration.md`) is a derived, regenerable view.

### Actual layout (differs slightly from `project_plan.md` §18.3's plan)

```text
src/living_narrative/
  pipeline/      8-phase turn driver (Load→…→Commit)
  agents/        world simulator, character, conflict resolver, narrator, checker, state manager
  state/         Pydantic v2 state schemas, store, StateDiff apply/rollback
  llm/           provider protocol, registry, mock + openai-compatible providers
  random/        seeded RNG, dice, weighted tables, roll log
  intervention/  structured intervention schema + interpreter
  session/       user mode, autonomy level, stop conditions, review gate, resume
  narration/     novel/log renderers
  export_replay/ replay.md exporter
  safety/        leak / continuity checkers
  workspace/     project.yaml load, init, workspace layout
  cli/           typer entry point (init/turn/auto/review/status/export)
  templates/     project templates: minimal, mist_station (sample world for smoke runs)
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

### Key locked decisions (spec-foundation §9, D101–D122)

CLI-only in batch 1, no web UI (D101); `typer` for the CLI (D102); YAML files are the source of truth, no DB (D103); `openai` SDK + configurable `base_url` for OpenAI-compatible/Ollama/LM Studio, LiteLLM rejected as unneeded (D104); Pydantic v2 is the single schema source of truth (D105); narrative content is Japanese-first, code/identifiers are English (D106); all state mutation goes through diffs, no exceptions (D107); extension points are `Protocol` + a plain registry dict, no plugin loader yet (D108); `unresolved_threads`/branching get a data format now, no runtime behavior until Phase 5 (D109).

D110–D122 (added during the Phase 0 self-grill) lock further details: LLM retry exhaustion → turn `failed` (D110); turn status persists in `meta.yaml`, written last as completion marker (D111); failed/rerun attempts are preserved as `turn_NNNN_discarded_<n>`, never overwritten (D112); diff generation is the BuildDiff slot implemented by State Manager (D113); the intervention-permission matrix's source of truth is session-autonomy (D114); `hidden_facts` are structured per-fact objects (D115); relationships are identified by the composite key `<from_id>__<to_id>` (D116); missing fixed state files fail fast on load (D117); commit-mode is a runtime parameter, not project.yaml schema (D118); `stop_condition` halts all autonomy levels including god (D119); `reject_all` turns keep artifacts but are excluded from replay export (D120); conflicts always resolve via rolls and events carry `roll_ids` (D121); named LLM profiles + bindings allow per-agent/per-character models (D122). See spec-foundation §9 for the full table.

### Naming/ID conventions (spec-foundation §3)

IDs are `<type>_<zero-padded-number>` (`char_001`, `event_0001`, `diff_0001`, `turn_0001`). Turn numbers are 1-based. `diff`/`event`/`roll`/`intervention` IDs are unique per-project across turns. Capability and doc filenames are kebab-case; YAML keys are snake_case; Python follows PEP 8.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **LivingNarrativeEngine** (5351 symbols, 10335 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/LivingNarrativeEngine/context` | Codebase overview, check index freshness |
| `gitnexus://repo/LivingNarrativeEngine/clusters` | All functional areas |
| `gitnexus://repo/LivingNarrativeEngine/processes` | All execution flows |
| `gitnexus://repo/LivingNarrativeEngine/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
