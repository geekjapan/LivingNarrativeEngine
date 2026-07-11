# LivingNarrativeEngine

共通のエージェント規約とオーケストレーション規約はグローバル`AGENTS.md`に従う。このファイルにはリポジトリ固有の指示だけを記載する。

## プロジェクト

LivingNarrativeEngineはPython 3.12+のstate-firstナラティブシミュレーションエンジンである。YAML状態と追記専用のevent、intervention、roll、diffログを正本とし、narrationは再生成可能な派生ビューとして扱う。

必要に応じて次の順に参照する。

1. `docs/issues/NNN-slug.md` — 現在の作業単位と完了条件。
2. `docs/adr/` — 承認済みのアーキテクチャ判断。
3. コードとテスト — 現行挙動の正本。
4. `docs/spec-foundation.md` — 共有契約と基礎判断。
5. `docs/project_plan.md` — 製品ビジョンとロードマップ。後続判断と異なる場合は参考情報とする。
6. `openspec/specs/` — 初回実装バッチの凍結リファレンス。

このリポジトリでは新規作業にOpenSpecを使わない。既存のarchiveとapplied specsは削除せず凍結参照として維持する。新規作業はIssueで管理し、永続的なアーキテクチャ判断はADRへ記録する。

## ワークフロー

- 依頼を扱う既存Issueがあればそれを使う。なければ`docs/issues/NNN-slug.md`を作り、`id`、`title`、`status`、`created`、背景、完了条件、関連ファイルを記載する。
- 製品・プロジェクト文書は日本語を第一言語とし、コードと識別子は英語にする。
- 実装状態とIssueのstatusを一致させる。
- 永続的なアーキテクチャ判断を追加・変更するときは`docs/adr/`へADRを追加する。
- コード変更前にGitNexusで関連flowとsymbol impactを調べ、commit前に`detect_changes`を実行する。

## コマンド

```bash
uv sync --extra web
NO_COLOR=1 uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
node .gitnexus/run.cjs analyze --index-only
```

反復中は対象testを使い、完了前に全checkを実行する。local smoke projectと生成runtime dataはgitignore済みの`sandbox/`または`projects/`に置く。実credentialを追跡対象ファイルへ保存しない。

## アーキテクチャ

- `src/living_narrative/pipeline/` — Load、Intervene、Simulate、Act、Resolve、Narrate、Check、Commitの8-phase turn pipeline。
- `src/living_narrative/agents/` — world、character、conflict、narrator、checker、state-managerのbehavior。
- `src/living_narrative/state/` — Pydantic v2 schema、永続化、atomicな`StateDiff`適用。
- `src/living_narrative/llm/` — provider protocol、registry、mock、OpenAI-compatible provider。
- `src/living_narrative/session/`、`intervention/`、`random/`、`narration/`、`safety/` — runtime policyと決定論的な補助system。
- `src/living_narrative/cli/`と`src/living_narrative/web/` — CLIとlocal webのentry point。
- `src/living_narrative/plugins/` — project-localかつallowlist制のplugin runtime。
- `tests/` — 上記境界を横断するbehavior test。

## 必須契約

- 状態変更はすべてatomicな`StateDiff`を経由する。直接の状態変更は禁止する。
- 情報scopeを維持する。character agentには本人の知識だけ、narrationにはreader-visible dataだけを渡し、生成するfactとeventにはvisibilityを付ける。
- seed付き乱数の決定性を維持し、replayに必要なrollをすべて記録する。
- 失敗時もpartial turn artifactを保存し、`meta.yaml`をcompletion markerとして最後に書く。
- Pydantic v2 modelをschemaの正本とする。YAML keyは`snake_case`、PythonはPEP 8、capability名と文書filenameは`kebab-case`にする。
- plugin loadは任意コード実行を伴うtrust boundaryである。明示的にallowlistされたinstalled pluginだけをloadし、登録はproject-localかつtransactionalに保つ。
- disclosure-safeなCLI/web出力に`gm_vault`、`hidden_facts`、character secrets、`private_mind`を含めない。

## 検証

behavior変更には、その変更なしでは失敗する最小のregression testを追加する。対象pathに加えて全test、lint、format、diff checkを実行する。security-sensitive、state schema、visibility、persistence、plugin、CLI/API、cross-module変更ではfocused integration coverageを追加し、GitNexus impact reportを確認する。
