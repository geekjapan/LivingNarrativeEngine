---
id: 040
title: シーン画像プロンプトexporter
status: in_progress
created: 2026-07-11
---

# 040: シーン画像プロンプトexporter

## 背景

Issue 039でキャラクター外見・背景・画風固定profileを保存できるようになったが、画像生成providerへ渡す一貫したシーン単位promptはまだ作れない。D-4に従い、画像自体は生成せず、既存の再構成・LLM profile機構を再利用して監査可能なexport成果物を生成する。

## 設計

1. `reconstruct_session` のシーン構造と、保存済みvisual profilesを入力に、シーンごとの日本語説明と英語prompt本文を生成する。
2. キャラクターごとの `CharacterVisualProfile`、背景profile、project全体のstyle lockを各promptへ明示的に含め、ターン間の外見一貫性を保つ。
3. novel/reviseと同じ `LLMGateway` + binding/profile選択方式を使い、CLIへ `living-narrative export image-prompts` subcommandと `--profile` を追加する。
4. `exports/image_prompts.yaml` と `exports/image_prompts.md` を出力し、両成果物のヘッダに「生成画像の権利・利用条件はproviderに依存する」旨を1行明記する。
5. LLM失敗・欠落profile・空sceneを明確に扱い、画像provider呼出しやcacheはIssue 041へ残す。

## 完了条件

- [ ] 再構成済みsceneとvisual profilesからシーン単位promptを生成する
- [ ] 日本語scene説明と英語prompt本文がある
- [ ] character/background/style-lockを参照し外見一貫性情報を保持する
- [ ] `export image-prompts --profile` が既存LLM binding方式で動作する
- [ ] `image_prompts.yaml` と `.md` がexports配下へ出力される
- [ ] 両成果物にprovider依存の権利注意書きがある
- [ ] 画像生成を先取りせず、全テスト・ruff check・ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/export_replay/reconstruction.py`
- `src/living_narrative/export_replay/image_prompts.py`
- `src/living_narrative/export_replay/__init__.py`
- `src/living_narrative/cli/export.py`
- `src/living_narrative/pipeline/llm_gateway.py`
- `tests/export_replay/`, `tests/cli/test_export_command.py`
