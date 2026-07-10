---
id: 050
title: サンプル世界と権利・セキュリティ文書
status: in_progress
created: 2026-07-11
---

# 050: サンプル世界と権利・セキュリティ文書

## 背景

mist_station以外の物語世界を選べず、secretを含む実用的な初期構成や画像生成・ローカル運用時の注意点も一か所にまとまっていない。雰囲気の異なる日本語サンプルを追加し、initから選択できる状態と、安全な利用判断に必要な文書を整える。

## 設計

1. 現代ミステリまたは宇宙站を題材に、3〜4人のcharacter、GM専用secret、hidden facts、factions、threats、quest、visual profilesを持つ日本語テンプレートを追加する。leak checkerが実際に秘密漏洩を検出できる構成にする。
2. template registryへ登録し、`living-narrative init --template`から選択可能にする。mist_stationと同等のモデル検証・参照整合・秘密情報検査をテストする。
3. 034と並列でテンプレート本体を実装し、034マージ後にmainを取り込んでquest fixtureの正規load検証を追加してからmergeする。
4. `docs/rights-and-security.md`に、画像生成providerごとの権利・利用条件確認、ローカル運用前提、API secretとGM秘密情報の取扱いを日本語第一で記載する。
5. READMEから注意書きへリンクし、quickstartに新テンプレートの選択例を追加する。

## 完了条件

- [ ] mist_stationと異なる日本語サンプル世界が1つ追加される
- [ ] character 3〜4人、GM秘密、hidden facts、factions、threats、quest、visual profilesを含む
- [ ] registry登録済みで`init --template`から選択できる
- [ ] モデル・参照整合・leak checkerを含むテンプレート検証テストがある
- [ ] `docs/rights-and-security.md`に画像権利、ローカル運用、秘密情報の注意がある
- [ ] READMEから注意書きと新テンプレートへ到達できる
- [ ] 034取込み後にquest fixtureの正規loadを検証している
- [ ] 全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/templates/registry.py`
- `src/living_narrative/templates/<new-template>/`
- `src/living_narrative/workspace/init.py`
- `docs/rights-and-security.md`
- `README.md`
- `tests/templates/`
- `tests/cli/test_init_command.py`
