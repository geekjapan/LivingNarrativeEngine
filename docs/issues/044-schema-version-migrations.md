---
id: 044
title: schema_version と migration 骨格
status: in_progress
created: 2026-07-11
---

# 044: schema_version と migration 骨格

## 背景

現状の `ProjectConfig` には永続化スキーマのバージョンがなく、`pipeline/version.py` の `PIPELINE_VERSION` はターン成果物にしか適用されない。E7〜E9では `CharacterState` などの正規スキーマを継続的に変更するため、互換性を判定し、将来のデータ移行を段階的に実行できる基盤を最初に用意する必要がある(D-5)。

## 設計

1. Pydantic v2の正本である `ProjectConfig` に `schema_version` を追加し、新規生成される `project.yaml` と同梱テンプレートへ現在バージョンを明記する。
2. project loader はバージョンを明示的に検査し、現在より新しい未対応バージョンを安全に拒否する。既存プロジェクトの扱いは後方互換性を保ちつつテストで固定する。
3. migration registry は整数バージョン `N` ごとの `N → N+1` 関数を登録・解決できる最小の骨格とし、欠落ステップ、重複登録、将来バージョンを明確なエラーにする。
4. migration は永続stateを直接mutationするランタイム経路にはしない。将来の移行実装がPydantic検証済みデータを生成できる責務境界を定める。

## 完了条件

- [ ] `ProjectConfig.schema_version` がPydantic v2スキーマの正フィールドとして定義され、新規project/templateに出力される
- [ ] loaderが対応中・既存互換・未対応の将来バージョンを期待どおり検査する
- [ ] `N → N+1` migration registryと、登録・連鎖・欠落・重複のテストがある
- [ ] 既存テストを含む全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係なファイル変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/state/models.py` (`ProjectConfig`)
- `src/living_narrative/state/validation.py` (`load_project_config`)
- `src/living_narrative/workspace/loader.py` (`load_project`)
- `src/living_narrative/workspace/init.py` と `src/living_narrative/templates/*/project.yaml`
- `src/living_narrative/workspace/migrations.py` (migration registry新設候補)
- `tests/test_models.py`, `tests/test_init.py`, `tests/session/test_project_config.py`
