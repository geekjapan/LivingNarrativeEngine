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
