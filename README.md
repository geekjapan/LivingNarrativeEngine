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
