# LivingNarrativeEngine

State-first, LLM-driven interactive narrative engine. See `docs/project_plan.md` and
`docs/spec-foundation.md` for the full design.

## Setup

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Usage

```bash
uv run living-narrative projects/mist_station --title "霧の駅"
```

Creates `projects/mist_station/project.yaml` plus a minimal empty-world `workspace/`
(state files, `runs/`, `exports/`). `add-cli-and-sample` adds the `turn`/`auto`/`export`
commands and a fleshed-out sample world.

## LLM Providers

`project.yaml` selects the provider through `llm.provider`. Use `mock` for tests and
offline smoke runs:

```yaml
llm:
  provider: mock
  model: mock-v1
  prompt_recording: full
```

Use `openai-compatible` for OpenAI, Ollama, or LM Studio compatible endpoints. API keys
come only from environment variables such as `OPENAI_API_KEY`; do not store them in
project files.

```yaml
llm:
  provider: openai-compatible
  model: gpt-4.1-mini
  base_url: https://api.openai.com/v1
  timeout_seconds: 30
  prompt_recording: hash_only
```

Named profiles can be bound per role or character with `llm_profiles` and
`llm_bindings`, for example `character:char_002: large_model`.

## Turn Pipeline

`TurnPipeline().run(project_path)` drives one turn through 8 phases (Load, Intervene,
Simulate, Act, Resolve, Narrate, Check, Commit; BuildDiff runs between Narrate and
Check) and writes `workspace/runs/turn_NNNN/`:

| file/dir | phase | contents |
|---|---|---|
| `intervention.yaml` | Intervene | this turn's interventions (always `[]` until `add-intervention`) |
| `agent_io/act.yaml` | Act | Character Agent LLM request/response records |
| `events.yaml` | Resolve | resolved `Event`s, project-wide unique `event_NNNN` ids |
| `rolls.yaml` | Resolve | dice/chance/table rolls (`[]` for the built-in pass-through slot) |
| `narration.md` | Narrate | YAML frontmatter (`turn`/`style`/`visibility: reader`) + prose/log body |
| `checks.yaml` | Check | checker findings (`info`/`warn`/`error`) |
| `state_diff.yaml` | Commit | the BuildDiff candidate, `rejected_changes`, and whether it was `applied` |
| `meta.yaml` | last, always | `status`, phase durations, LLM call log, `rng_draws_consumed`, `pipeline_version` |

`meta.yaml.status` is one of `applied` / `pending_review` / `stopped_for_review` /
`failed`; it is written last as the turn's completion marker, so a `turn_NNNN` dir with
no readable `meta.yaml` is treated as unresolved and blocks the next turn. A retried
`failed` turn moves its old directory to `turn_NNNN_discarded_<n>` first — old artifacts
are never overwritten.

Simulate/Act/Resolve/BuildDiff/Check are registry-swappable slots
(`living_narrative.pipeline.default_registry()`); this change ships only minimal
built-ins (no-op Simulate/Check, trivial single-character Act, pass-through Resolve, and
an empty-diff BuildDiff) so a turn completes end-to-end with just the mock provider.
`add-agent-runtime` replaces these with the real Character/World/Conflict/State Manager
agents.
