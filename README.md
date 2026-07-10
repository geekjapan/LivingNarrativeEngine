# LivingNarrativeEngine

State-first, LLM-driven interactive narrative engine. See `docs/project_plan.md` and
`docs/spec-foundation.md` for the full design.

## Setup

```bash
uv sync --extra web
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Quickstart

### Local (uv)

Install [uv](https://docs.astral.sh/uv/), then run the following commands from this
repository's root:

```bash
uv sync --extra web

uv run living-narrative init \
  --title "軌道站エコー" \
  --template orbital_echo \
  --output projects/orbital_echo

uv run living-narrative serve \
  --project-root projects \
  --port 8000
```

Open <http://127.0.0.1:8000> in a browser. Stop the server with `Ctrl+C`.

### Docker Compose

Docker Compose mounts the local `projects/` directory into the container, so projects and
their run artifacts remain on the host. Build the image and create the sample project once:

```bash
docker compose build

docker compose run --rm app living-narrative init \
  --title "霧の駅" \
  --template mist_station \
  --output /projects/mist_station

docker compose up
```

Open <http://127.0.0.1:8000>. The Compose port is deliberately published only on the host's
loopback interface. Stop and remove the container and network with:

```bash
docker compose down
```

### OpenAI-compatible gateway

The sample project uses the mock provider. To use an OpenAI-compatible gateway, copy the
environment template and edit the untracked `.env` file:

```bash
cp .env.example .env
```

```dotenv
OPENAI_BASE_URL=https://gateway.example.com/v1
OPENAI_API_KEY=replace-with-your-real-secret
```

`OPENAI_BASE_URL` selects the gateway endpoint and `OPENAI_API_KEY` supplies its credential.
Also change the project's `llm.provider` to `openai-compatible` and choose a model. Compose
loads `.env` automatically; local uv commands inherit variables exported by your shell (for
example, `set -a; . ./.env; set +a`). Never commit `.env` or put a real secret in
`project.yaml`, `compose.yml`, or `.env.example`; `.env` is ignored by Git and excluded from
the Docker build context.

### CLI workflow

After creating a project, the CLI can also advance and export it directly:

```bash
uv run living-narrative turn \
  --project projects/mist_station/project.yaml

uv run living-narrative auto \
  --project projects/mist_station/project.yaml \
  --turns 5

uv run living-narrative export replay \
  --project projects/mist_station/project.yaml \
  --output projects/mist_station/workspace/exports/replay.md
```

`init --template` accepts `orbital_echo` (the Japanese hard-SF "軌道站エコー" sample:
3 characters, factions, threats, visual profiles, and a quest fixture), `mist_station`
(the "霧の駅" sample world), or `minimal` (an empty, schema-valid workspace; the default
when `--template` is omitted). `--genre`/`--tone` are optional free-text fields written
straight through to `project.yaml`.

`turn` runs a single turn and prints its narration + status line. `--intervention "<free
text>"` routes through the Intervention Interpreter (LLM); `--type <type> --target <id>
--content "<text>"` is a direct-input path with no LLM call. `--as <user_mode>`
temporarily overrides `user_mode` for that turn only (`project.yaml` is restored
afterward) — `--as player_character` is rejected, since that mode requires a session
`char_id` binding it can't express as a one-off override.

`auto --turns N` advances up to N turns, stopping early if session-autonomy's stop
conditions fire (printing which one). `auto --until scene_end` instead runs until the
active scene ends.

`review --project <path>` presents the pending/stopped-for-review turn's state diff and
resolves it via `--decision accept_all|reject_all|partial|edit|rerun_turn` (matching
`review.yaml`'s canonical decision values 1:1) — `partial` takes `--apply <index,...>`,
`edit` takes `--patch <file>` (a full replacement `StateDiff` as YAML), and `rerun_turn`
takes an optional `--replay-same-seed` to rewind the RNG to the turn's original position
instead of continuing forward. Every decision is available non-interactively; with no
TTY and no `--decision`, the command exits `2` rather than blocking.

`status --project <path>` (add `--json` for machine-readable output) reports the current
turn, pending-review state, `user_mode`/`autonomy_level`, and a scene/world-parameter
summary — never `gm_vault`, `hidden_facts`, `secrets`, or `private_mind`, regardless of
`user_mode`.

Exit codes: `0` success, `1` runtime failure (a `failed` turn, provider error, nothing to
export), `2` invalid input (bad flags, unknown template, missing project).

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
| `intervention.yaml` | Intervene | this turn's interventions (free-text via the Interpreter, or direct-input) |
| `agent_io/act.yaml` | Act | Character Agent LLM request/response records |
| `events.yaml` | Resolve | resolved `Event`s, project-wide unique `event_NNNN` ids |
| `rolls.yaml` | Resolve | dice/chance/table rolls (World Simulator always rolls at least a background event) |
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
(`living_narrative.pipeline.default_registry()`), backed by the real World Simulator /
Character Agent / Conflict Resolver / State Manager / leak+continuity checkers
(`living_narrative.agents`, `living_narrative.safety`) — a turn completes end-to-end with
just the mock provider and no fixtures.

## Export Replay

`export replay --project <path> --output <file> --style novel|log` assembles every
`applied` turn's `narration.md` into `replay.md`, purely from saved turn artifacts (no
LLM calls; re-running produces a byte-identical file). `novel` concatenates prose only;
`log` also annotates each turn with its interventions, reader-visible rolls (only rolls
reachable from a `reader`-visible event's `roll_ids`), and applied diff changes.
`pending_review`/`stopped_for_review`/`failed` turns, and `applied` turns whose
`review.yaml` decision was `reject_all`, are gaps: `log` inserts a placeholder noting the
status, `novel` skips them with no annotation at all. `gm_vault`, `hidden_facts`,
`secrets`, and `private_mind` are never read by this command.

## Security

Before connecting a generation provider or sharing a project, read the Japanese-first
[rights and security guidance](docs/rights-and-security.md). It covers image-generation
rights, provider-dependent terms, the local-only operating assumption, API credentials,
and GM-only narrative information.

- API keys come only from environment variables (e.g. `OPENAI_API_KEY`); never commit
  them to `project.yaml` or any tracked file. Use a local `.env` (already `.gitignore`d)
  with `openai-compatible` projects.
- A project's `workspace/` is expected to be private: turn artifacts, prompt records, and
  `gm_vault`/`secrets`/`private_mind` all live there in plain YAML.
- CLI commands never print or log `gm_vault`, `hidden_facts`, character `secrets`, or
  `private_mind` (`status`, in particular, always returns a disclosure-safe summary
  regardless of `user_mode`), and API keys never appear in error messages or artifacts.
