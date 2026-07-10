---
id: 041
title: 画像provider interfaceとasset cache
status: done
created: 2026-07-11
---

# 041: 画像provider interfaceとasset cache

## 背景

Issue 040で監査可能な画像promptは生成できるが、providerへ委譲する標準境界、同一promptの再利用、生成物の採用判断を記録する仕組みがない。D-4に従いエンジン固有の実providerは持たず、mockとローカルcacheで拡張点を固定する。

## 設計

1. `media/`に`ImageProvider` Protocol（`generate(prompt, profile)`）とplain dict registryを追加し、`llm/registry.py`と同じ登録・生成・unknown provider errorの流儀にする。
2. built-inは決定論的mockだけとし、prompt hashから安定したplaceholder assetを生成する。OpenAI互換等の実画像providerは実装しない。
3. `exports/assets/`へassetと`assets.yaml`をatomicに保存する。entryはprompt hash、provider/profile、path、generated_at、`pending | accepted | discarded`の採否状態、権利注意書きをPydantic v2で検証する。
4. 同一prompt hashとprovider/profileの既存assetはcache hitとして再生成せず再利用する。履歴の既存entryを失わない。
5. `image_prompts.yaml`から生成するCLIと、対象assetのaccept/discardを行う軽量CLIを追加する。path traversal、unknown asset、不正manifestを境界で拒否する。
6. 出力metadataと`docs/rights-and-security.md`へ、生成物の権利・利用条件・データ保持がproviderに依存する旨を追記する。

## 完了条件

- [x] `ImageProvider` Protocolとdict registry、unknown provider errorがある
- [x] 決定論的mock providerだけがbuilt-in登録される
- [x] `exports/assets/`とatomicな`assets.yaml`へ生成履歴を保存する
- [x] 同一prompt/provider/profileはcache hitとなり再生成されない
- [x] pending/accepted/discardedをCLIまたは安全なmanifest経路で更新できる
- [x] path traversal、不正manifest、unknown assetを拒否する
- [x] output metadataと権利・セキュリティ文書にprovider依存リスクがある
- [x] 実画像providerを先取りせず、全テスト・ruffがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 完了記録

実装commitは`87acfb4`。レビューで`exports/assets`および`assets.yaml`のsymlink escapeを拒否する境界と回帰テストを追加し、Wave 6最終統合状態で886 testsとruffの通過を確認した。

## 関連ファイル

- `src/living_narrative/media/`
- `src/living_narrative/export_replay/image_prompts.py`
- `src/living_narrative/cli/export.py`
- `docs/rights-and-security.md`
- `tests/media/`
- `tests/cli/test_export_command.py`
