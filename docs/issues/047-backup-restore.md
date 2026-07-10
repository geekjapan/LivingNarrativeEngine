---
id: 047
title: プロジェクトbackup/restore CLI
status: done
created: 2026-07-11
---

# 047: プロジェクトbackup/restore CLI

## 背景

現状はbranch作成時の `copy_project_for_branch` がproject directory全体を複製するだけで、運用向けのbackup/restore導線と出自情報がない。Issue 044の `schema_version` 基盤を利用し、圧縮や外部ストレージを持ち込まない最小のディレクトリbackupをCLIとして提供する。

## 設計

1. `living-narrative backup --project <project.yaml> --output <dir>` はproject directory全体を、output配下の衝突しないtimestamp付きdirectoryへコピーする。
2. backup rootの `manifest.yaml` に元project path、作成日時、`schema_version` を記録する。backup対象へmanifestを混入させず、restoreが検証・表示できる明確な形式にする。
3. `living-narrative restore <backup> --output <dir>` はmanifestとproject layoutを検査して復元し、manifestのschema_versionをCLI出力へ明示する。
4. restore/backupとも既存の非空directoryを上書きしない。失敗時に部分コピーを残さないか、残る可能性を明確に制御する。
5. `copy_project_for_branch` のcopy primitiveを共通workspace helperへ昇格して再利用してよいが、branch/rollbackの既存挙動を変えない。圧縮形式はスコープ外とする。

## 完了条件

- [x] backup CLIがproject directory全体をtimestamp付きdirectoryへコピーする
- [x] manifest.yamlに元path・作成日時・schema_versionが記録される
- [x] restore CLIがbackupから独立project directoryを復元し、schema_versionを表示する
- [x] backup/restoreが既存非空directoryの上書きを拒否する
- [x] manifest欠落・不正backup・copy失敗などの境界テストがある
- [x] 既存branch/rollbackの回帰がなく、全テスト・ruff check・ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## レビュー時の是正

初回実装後の二軸レビューで、backup側のatomic publish/cleanup手順が共通copy primitiveと重複している点を是正した。`publish_directory_atomic` を共通化し、backup/restore双方のcopy失敗時にpartial destinationと一時directoryを残さない回帰テストを追加して既存commitへamendした。

## 関連ファイル

- `src/living_narrative/session/rollback.py` (`copy_project_for_branch`)
- `src/living_narrative/workspace/backup.py`, `src/living_narrative/workspace/copy.py`
- `src/living_narrative/cli/__init__.py`
- `src/living_narrative/cli/branch.py`
- `src/living_narrative/cli/backup.py` (`backup` / `restore`)
- `tests/cli/test_rollback_branch.py`, `tests/cli/` backup/restore tests
