# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

This repository is a greenfield project — the only committed content is `README.md` (a title) and `AGENTS.md` (contributor guidelines). There is **no source code, `package.json`, build tooling, test runner, or lint config yet.** Do not assume any exist; verify before referencing them.

When the first real tooling lands (package manager, build/test/lint commands, source layout), document the exact commands and the high-level architecture here, and keep this file in sync with `AGENTS.md`.

## Conventions (from AGENTS.md)

`AGENTS.md` is the source of truth for structure and style until code exists. Key points to apply to new code:

- Intended layout: `src/` (source), `tests/` mirroring source paths, `assets/` (narrative content/fixtures), `docs/` (design notes, ADRs). Prefer shallow, descriptive module paths.
- `camelCase` for JS/TS variables and functions, `PascalCase` for classes/components/exported types, `kebab-case` for doc and asset filenames. Two-space indentation.
- Add a test with the first non-trivial behavior; name test files after the unit (`src/parser.js` → `tests/parser.test.js`). Every bug fix ships the smallest regression test that would fail without it.
- Short imperative commit subjects (e.g. `Add parser smoke test`).
- Don't add wrapper scripts or speculative scaffolding until a command contributors actually run needs them.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **LivingNarrativeEngine** (16 symbols, 12 relationships, 0 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
