---
id: 048
title: Docker ComposeとREADME quickstart
status: done
created: 2026-07-11
---

# 048: Docker ComposeとREADME quickstart

## 背景

CLIとweb UIは利用可能だが、新規ユーザーが依存関係、project作成、web起動をREADMEだけで再現できる導線がなく、コンテナ実行定義もない。E9の受入条件に合わせ、ローカルuv経路とloopback限定Docker Compose経路を最小構成で整備する。

## 設計

1. Python 3.12-slimとuvを基盤に、web extraを導入して `living-narrative serve` をport 8000で起動するDockerfileを追加する。
2. `compose.yml` はhost側を必ず `127.0.0.1:8000:8000` で公開し、project directoryをvolumeとして渡す。application内部の既存loopback固定は変更しない。
3. README quickstartに、uvでのinit/serveとdocker composeでのbuild/init/serve、ブラウザURL、停止方法を実行順に記載する。
4. OpenAI-compatible gatewayは `OPENAI_BASE_URL` / `OPENAI_API_KEY` の環境変数で指定できることを説明し、秘密をコミットしない `.env.example` とgitignore規約を整える。
5. dockerが利用可能ならbuildを1回実行し、利用不可なら理由をissueへ明記する。

## 完了条件

- [x] Python 3.12-slim + uvのDockerfileでweb serveを起動できる
- [x] composeの公開portが `127.0.0.1:8000:8000` に限定される
- [x] READMEだけでuvローカル起動とDocker Compose起動を完遂できる
- [x] `OPENAI_BASE_URL` / `OPENAI_API_KEY` の設定方法があり、秘密のハードコードがない
- [x] `.env.example` があり、実 `.env` はgitignoreされる
- [x] docker buildを検証済み、または環境理由のskipをissueに明記する
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 検証記録

- 2026-07-11: Docker 29.5.3 / Docker Compose v5.1.4で`docker compose config`、
  `docker compose build`、コンテナ内`init`、`docker compose up`後の
  `http://127.0.0.1:8000/`へのHTTP 200応答を確認。
- 2026-07-11: `NO_COLOR=1 uv run pytest`、`uv run ruff check .`、
  `uv run ruff format --check .`を実行。
- 2026-07-11: GitNexus upstream impactはrisk LOW（direct caller 0、影響process 0）。
  commit前に`detect_changes(scope=compare, base_ref=main)`で確認。

## 関連ファイル

- `Dockerfile`
- `compose.yml`
- `.dockerignore`
- `.env.example`
- `.gitignore`
- `README.md`
- `src/living_narrative/cli/serve.py`
- `tests/web/test_server_host.py`
