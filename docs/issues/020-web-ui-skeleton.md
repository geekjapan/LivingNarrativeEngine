---
id: 020
title: Web UI骨格(FastAPI、localhost限定、状態正本はファイルのままの薄い読み書き層)
status: done
created: 2026-07-07
---

# 020: FastAPI骨格(Track B起点)

## 背景

DAG(docs/plan/feature-dag.md)Track B起点。Phase 4「Web UI / GM Cockpit」の土台。D103: YAMLファイルが状態の正本 — UIはDBを持たず、既存の workspace/session/pipeline API を呼ぶ薄い窓に徹する。

## 設計

1. `src/living_narrative/web/` 新設: FastAPI app。既存コードへの変更は最小(既存モジュールをimportして使うのみ、コア側の改変禁止)
2. **localhost bindのみ**(`127.0.0.1` 固定、設定で変更不可 — セキュリティ最低線。テストで保証)
3. エンドポイント(この issue の範囲):
   - `GET /api/projects?root=DIR` — DIR配下の project.yaml 列挙
   - `GET /api/project/{...}/status` — 現在ターン・シーン・キャラ概要(既存status相当)
   - `GET /api/project/{...}/narration?from=N` — narration.md 連結(reader可視のみ)
   - `POST /api/project/{...}/turn` — 1ターン実行(commit_mode等は既存デフォルト)
   - 最小のHTML(1ページ、素のfetch — フレームワーク導入はTrack B後続で判断)
4. 依存は uv optional extra `web`(fastapi + uvicorn)。CLI: `living-narrative serve --project-root DIR`
5. 長時間ターン実行のブロッキングは当面許容(非同期化は022で扱う)

## 完了条件

- [x] `uv sync --extra web` で入り、`living-narrative serve` が127.0.0.1で起動
- [x] 上記4エンドポイントがmockプロジェクトで動く(httpxテスト)
- [x] 127.0.0.1以外へのbindが不可能であることのテスト
- [x] narrationエンドポイントがreader可視のみ返す(gm_only混入なしのテスト)
- [x] 既存テストに影響ゼロ(web未インストール環境でもコアが壊れない: importガード)

## 関連ファイル

- 新規: `src/living_narrative/web/`(app.py, server.py, service.py, page.py)、`src/living_narrative/cli/serve.py`、`pyproject.toml`(extra)、`tests/web/`、`tests/cli/test_serve_command.py`
- 参照のみ: `workspace/loader.py`、`pipeline/driver.py`、`cli/`(serveサブコマンド追加は cli/ に薄く)
- DAG: `docs/plan/feature-dag.md`

## 実装時の逸脱(deviation)

- `GET /api/projects` は設計文中では `?root=DIR` クエリだが、実装では `--project-root` で起動時に固定した root を使う(クエリでの任意 root 指定は許可しない)。理由: `{name}` のパストラバーサル対策と一貫させるため — 任意の root を都度受け付けると「サーブ対象を起動時に絞る」というセキュリティ境界そのものが崩れる。
