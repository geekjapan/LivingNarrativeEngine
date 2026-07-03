# Proposal: add-project-foundation

## Why

Living Narrative Engine には現時点でリポジトリの土台(パッケージ構成・依存管理・CI・`project.yaml` スキーマ・workspace レイアウト)が存在しない。以降のすべての change(`add-state-model` 以降、DAG 全体)はプロジェクトの読み込み・workspace 構造に依存するため、最初に単独で成立する土台を確立する必要がある。

## What Changes

- `uv` 管理の `pyproject.toml` を追加し、パッケージ `living_narrative` を `src/living_narrative/` レイアウトで作成する(Python 3.12+)。
- dev 依存として `pytest`・`ruff`(lint + format)を導入する。
- GitHub Actions CI ワークフローを追加する(`uv sync` → `ruff check` → `ruff format --check` → `pytest`)。
- `project.yaml` の Pydantic v2 モデルを実装する(企画書 Appendix B 準拠のフィールド構成、`language` 既定値 `"ja"`)。ロード時にファイル単位・フィールド単位でエラーを集約報告する検証ロジックを実装する。未知フィールドは警告のみで失敗させない。
- workspace ディレクトリレイアウト(企画書 Appendix C 準拠)を定義し、`living-narrative init` コマンド(typer スケルトン)で最小の空ワールドテンプレートから新規プロジェクトを生成できるようにする。既存ディレクトリへの上書きは拒否する。
- project 読み込み API(`project.yaml` の位置を基準に workspace パスを解決し、必須 state ファイルの存在を確認し、検証結果をレポートとして返す)を実装する。
- API キーなどの秘密情報をログに出さないための取り扱い方針を適用し、`.env` / `.gitignore` を整備する。
- `README.md` にセットアップ手順の最小限の記載を追加する。

## Capabilities

### New Capabilities
- `project-workspace`: `project.yaml` スキーマ・workspace レイアウト・`init`/load API・リポジトリ開発ツールチェーン(uv/pytest/ruff/CI)を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- `living-narrative` の完全な CLI コマンド群(`turn` 等)は `add-cli-and-sample` の範囲であり、本 change では `init` のみを扱う。
- `project.yaml` 以外の state ファイル(`world.yaml` / `characters/*.yaml` 等)のスキーマ定義は `add-state-model` の範囲であり、本 change では扱わない。
- Web UI(FastAPI/HTMX 等)は第1バッチの非ゴールであり、本 change でも実装しない。
- DB(SQLite 等)は導入しない。状態の正本はファイルとする(spec-foundation D103)。
- `init` で生成するテンプレートの物語コンテンツ自体(サンプル世界 `mist_station` のキャラクター・シーン内容)は `add-cli-and-sample` が提供する。本 change では検証を通す最小限の空ワールドテンプレートのみを用意する。
- LLM provider に対する API キーの環境変数からの読み取り・有無検証・接続処理は `add-llm-provider` の範囲であり、本 change は `project.yaml` の `llm` フィールドを値として保持するのみで、これらを実装しない。

## Dependencies

なし。本 change は依存 DAG の起点であり、`add-state-model` 以降のすべての change はこの change の完了を前提とする。

## Impact

- 新規: `pyproject.toml`, `src/living_narrative/`(パッケージ初期構成), `tests/`, `.github/workflows/`(CI), `README.md` 追記, `.gitignore` / `.env.example`。
- 影響を受ける既存コード: なし(greenfield)。
