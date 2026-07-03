## 1. リポジトリセットアップ

- [ ] 1.1 `pyproject.toml` を作成し、`uv` 管理・パッケージ名 `living_narrative`・Python 3.12+ requires-python を設定する
- [ ] 1.2 `src/living_narrative/` レイアウトで空パッケージ(`__init__.py`)を作成する
- [ ] 1.3 dev dependency group に `pytest`・`ruff` を追加する
- [ ] 1.4 `ruff` の lint/format 設定(`[tool.ruff]`)を `pyproject.toml` に追加する
- [ ] 1.5 `tests/` ディレクトリを作成し、`uv run pytest` が(空でも)成功することを確認する
- [ ] 1.6 GitHub Actions ワークフロー(`.github/workflows/ci.yml`)を追加し、`uv sync` → `ruff check .` → `ruff format --check .` → `uv run pytest` を実行する
- [ ] 1.7 `.gitignore` を整備する(`.venv/`, `__pycache__/`, `.env`, workspace の実行時生成物 等)
- [ ] 1.8 `.env.example` を追加し、秘密情報を平文でコミットしない運用を明示する

## 2. project.yaml スキーマ

- [ ] 2.1 `living_narrative/state/models.py`(または同等の配置)に `ProjectConfig` Pydantic v2 モデルを実装する(`id`, `title`, `genre`, `tone`, `language`(既定 `"ja"`), `autonomy_level`, `user_mode`, `random_seed`, `renderer`, `llm`, `workspace`)
- [ ] 2.2 `llm` サブモデル(`provider`, `model`, 任意 `base_url`)を実装する
- [ ] 2.3 `workspace` サブモデル(`root`, `state`, `runs`, `exports`)を実装する
- [ ] 2.4 未知フィールドを警告扱いにする設定(`model_config` の extra ハンドリング + 警告ログ)を実装する
- [ ] 2.5 単体テスト: 企画書 Appendix B 準拠の `project.yaml` が正しくロードされることを確認する
- [ ] 2.6 単体テスト: `language` 未指定時に `"ja"` が補完されることを確認する
- [ ] 2.7 単体テスト: 未知フィールドを含む `project.yaml` がロード成功し警告を発することを確認する

## 3. ロード時検証とエラー集約

- [ ] 3.1 `project.yaml` 読み込み関数を実装し、`ValidationError` をファイルパス・フィールド名・理由を含むレポート形式に整形する
- [ ] 3.2 秘密情報(API キー等)が `project.yaml` 検証エラー・ログに含まれないことを保証する実装/レビューを行う(本 change は API キーの環境変数読み取り・有無検証は行わない。責務は `add-llm-provider`)
- [ ] 3.3 単体テスト: 複数フィールドが不正な `project.yaml` で全エラーが集約されることを確認する
- [ ] 3.4 単体テスト: `llm.provider` 等のフィールド値が不正な `project.yaml` の検証エラーメッセージに、`.env`/環境変数由来の秘密情報の値が含まれないことを確認する

## 4. workspace レイアウトと init コマンド

- [ ] 4.1 workspace レイアウト定義(必須ディレクトリ・必須ファイル一覧)を定数として実装する
- [ ] 4.2 最小の空ワールドテンプレート(state ファイル一式の最小内容)を実装する
- [ ] 4.3 `living-narrative` typer app のエントリポイントを作成し、`init` サブコマンドを実装する(`--title` 必須オプション、出力先パス)。`--title` 以外のフィールドは spec の固定既定値(id: title から生成した slug、genre/tone: 空文字列、autonomy_level: `manual`、user_mode: `watcher`、random_seed: 自動生成、renderer: `novel`、llm.provider: `mock`、llm.model: `mock-v1`、workspace: Appendix B 準拠の相対パス)を用いる
- [ ] 4.4 既存の空でない出力先ディレクトリに対する上書き拒否ロジックを実装する
- [ ] 4.5 単体テスト: `init` 実行後に workspace レイアウトが規定どおり生成されることを確認する
- [ ] 4.6 単体テスト: 既存ディレクトリへの `init` がエラーになり、既存ファイルが変更されないことを確認する

## 5. プロジェクト読み込み API

- [ ] 5.1 `project.yaml` パスを起点に `workspace.*` の相対パスを解決する関数を実装する
- [ ] 5.2 必須 state ファイルの存在確認ロジックを実装し、欠落ファイル一覧を含む検証レポートを返す
- [ ] 5.3 単体テスト: 相対パスによる workspace 解決が正しいことを確認する
- [ ] 5.4 単体テスト: state ファイルが一部欠落したプロジェクトの読み込みが失敗し、欠落ファイル名がレポートに含まれることを確認する

## 6. ドキュメント

- [ ] 6.1 `README.md` に `uv sync` によるセットアップ手順と `living-narrative init` の最小利用例を追記する
- [ ] 6.2 `docs/spec-foundation.md` と矛盾がないことを確認する(project.yaml フィールド構成・workspace レイアウト)
