---
id: 049
title: plugin SDK形式化とE9品質ゲート
status: in_progress
created: 2026-07-11
---

# 049: plugin SDK形式化とE9品質ゲート

## 背景

LLM provider、checker、renderer、pipeline slot、image provider、voice providerは既存のProtocolとレジストリで拡張できるが、外部パッケージから安全に登録する公開経路と導入手順がない。Issue 049では既存境界を置換せず薄いentry-point発見層を追加し、明示的に有効化した信頼済みpluginだけをロードする。

## 設計

1. entry-point groupは`living_narrative.plugins`の単一groupとする。列挙したentry pointを`name`でallowlist照合し、許可済みの名前に対してだけ`EntryPoint.load()`を呼ぶ。
2. `ProjectConfig.plugins`をdefault空のallowlistとして追加する。非破壊的なoptional追加のため`schema_version`は1に据え置き、旧project.yamlをそのまま読み込めるようにする。
3. plugin宣言は既存6種のレジストリへ登録する薄いSDK境界だけを提供する。新しい操作経路やWeb/API経路を作らず、`session/mode.py`、`_require_*`、`can_view_gm_vault`等の既存権限境界を迂回させない。
4. allowlistにある未インストールpluginとロード失敗は明確に報告する。失敗を握りつぶさず、他のpluginとengine全体は継続可能にする。
5. plugin loadは任意コード実行を伴う信頼境界であり、今回sandbox実行機構は作らない。自動発見・自動実行を禁止し、信頼できるpluginだけを明示的にインストール・有効化する方針をADRとSDK文書へ記録する。

## 完了条件

- [ ] 6種の既存レジストリへ外部pluginがentry point経由で登録できる
- [ ] allowlist外entry pointでは`load()`が一度も呼ばれない
- [ ] allowlist内pluginだけが登録され、未インストール名とロード失敗が明確に報告される
- [ ] 旧project.yamlがmigrationなしで読め、`schema_version: 1`を維持する
- [ ] plugin登録面が既存の権限・情報スコープ境界を迂回しない
- [ ] `docs/plugin-sdk.md`とADRに実装例、有効化手順、信頼境界を日本語第一で記載する
- [ ] mock entry pointによる発見・照合・登録テストがpassする
- [ ] README起動、backup/restore、migration、plugin追加方法、権利・セキュリティ注意のE9完了条件を確認する
- [ ] 全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 関連ファイル

- `pyproject.toml`
- `src/living_narrative/state/models.py`
- `src/living_narrative/plugins/`
- `src/living_narrative/llm/registry.py`
- `src/living_narrative/safety/registry.py`
- `src/living_narrative/narration/renderers.py`
- `src/living_narrative/pipeline/registry.py`
- `src/living_narrative/media/registry.py`
- `src/living_narrative/media/voice_registry.py`
- `docs/plugin-sdk.md`
- `docs/adr/`
- `tests/plugins/`
