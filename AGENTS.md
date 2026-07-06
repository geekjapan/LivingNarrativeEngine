# Repository Guidelines

## Project Structure & Module Organization

This repository is currently minimal: the root contains `README.md` and no committed source, test, asset, or build directories yet. Keep new project files organized from the start:

- `src/` for application or engine source code.
- `tests/` or `test/` for automated tests.
- `assets/` for static data, fixtures, images, or narrative content.
- `docs/` for design notes, architecture decisions, and contributor-facing documentation.

Prefer shallow, descriptive module paths over broad catch-all folders. If a new subsystem is added, place its tests near the behavior they verify or mirror the source path under `tests/`.

## Build, Test, and Development Commands

No package manager, build script, or test runner is committed yet. When tooling is introduced, document the exact commands here and in `README.md`.

Expected examples:

- `npm test` or equivalent: run the full automated test suite.
- `npm run lint`: check formatting and style.
- `npm run build`: produce a distributable build.
- `npm run dev`: start a local development process.

Do not add wrapper scripts until they replace a command contributors actually need to run.

## Coding Style & Naming Conventions

Use the style of the first committed implementation unless a formatter is added. Keep names explicit and domain-focused. Prefer:

- `camelCase` for JavaScript or TypeScript variables and functions.
- `PascalCase` for classes, components, and exported types.
- `kebab-case` for documentation and asset filenames.

Use two-space indentation for JavaScript, TypeScript, JSON, YAML, and Markdown unless project tooling later specifies otherwise.

## Testing Guidelines

Add tests with the first non-trivial behavior. Name test files after the unit or workflow under test, such as `src/parser.js` with `tests/parser.test.js`. Each bug fix should include the smallest regression test that would fail without the fix.

## Commit & Pull Request Guidelines

Current history only contains `Initial commit`, so no project-specific convention exists yet. Use short imperative commit subjects, for example `Add parser smoke test`.

Pull requests should include a concise summary, validation performed, linked issue if one exists, and screenshots or sample output when user-facing behavior changes.

## Agent-Specific Instructions

Before editing, check whether project tooling has been added since this guide was written. Keep changes narrow, avoid speculative scaffolding, and update this file only when repository conventions actually change.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **LivingNarrativeEngine** (5186 symbols, 10051 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
