---
id: 049
title: plugin SDK形式化とE9品質ゲート
status: done
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
6. registryはprojectごとにbuilt-inからcloneし、plugin単位のtransactionで登録する。名前衝突や登録途中の例外ではplugin全体をrollbackし、global・別projectへ登録を漏らさない(`PluginRuntime`、下記「project-localランタイム設計」参照)。
7. 固定6種のレジストリ範囲を拡張しない(新しいpipeline slot種別やvoice export CLIは追加しない)。plugin登録処理自体は既存6種のみを対象とする。

### project-localランタイム設計(セキュリティレビュー是正、2026-07-11)

初期実装(built-inレジストリへ直接登録)には4つの問題があった: (#1)`load_plugins`が
production未配線、(#2)`register_*`がglobalの`register_provider`等を直接呼びbuilt-in名を
上書き可能、(#3)複数登録するpluginが途中失敗すると部分登録がglobalに残る、(#4)project間で
global registryが共有され、allowlist空のprojectにも他projectのplugin登録が漏れる。

是正として`PluginRuntime`(`src/living_narrative/plugins/sdk.py`)を導入した。

- 構築時にbuilt-in 6レジストリ(llm provider dict、safety `CHECKERS`、`RendererRegistry`、
  `SlotRegistry`、image/voice provider dict)を`clone()`でproject-localな浅いコピーとして
  複製する。`PluginSDK`はこのlocal viewにのみ登録し、global dict/レジストリを直接呼ばない
  (#2, #4 是正)。
- `load_plugins`はplugin単位でtransactionalに動作する: 各pluginの`register(sdk)`呼び出し前に
  runtimeを`clone()`してstaging領域を作り、登録処理をそこへ集める。built-in名または
  既に確定した名前と衝突した場合は`PluginCollisionError`を送出してplugin全体をreject
  (`reason: collision`)、登録後に別の例外が出た場合も同様にstagingごと破棄する。全て成功
  した場合だけ`adopt()`でlocal viewへcommitする(#3 是正)。
- production配線: `create_plugin_runtime(project, ...)`が`TurnPipeline.run`
  (`pipeline/driver.py`、slot/checker/renderer)、`LLMGateway`(`pipeline/llm_gateway.py`、LLM
  provider)、`living-narrative export images`(`cli/export.py`、image provider)へ渡される
  (#1 是正)。voice providerも同じruntime factoryから取得できる形にしてあるが、production側の
  voice export CLIは本issueのscope外(既存範囲を拡張しない、上記7)。
- 後方互換: 既存呼び出し箇所は`runtime`引数なしでも動く(`LLMGateway.__post_init__`が
  未指定時に自身の`project`から`create_plugin_runtime`を構築)。`project.plugins`が空の
  projectでは`PluginRuntime`はbuilt-inのcloneに過ぎず、挙動はplugin導入前と同一(既存950
  テストが無変更で通ることで保証)。

## 完了条件

- [x] 6種の既存レジストリへ外部pluginがentry point経由で登録できる
- [x] allowlist外entry pointでは`load()`が一度も呼ばれない
- [x] allowlist内pluginだけが登録され、未インストール名とロード失敗が明確に報告される
- [x] 旧project.yamlがmigrationなしで読め、`schema_version: 1`を維持する
- [x] plugin登録面が既存の権限・情報スコープ境界を迂回しない
- [x] `docs/plugin-sdk.md`とADRに実装例、有効化手順、信頼境界を日本語第一で記載する
- [x] mock entry pointによる発見・照合・登録テストがpassする
- [x] README起動、backup/restore、migration、plugin追加方法、権利・セキュリティ注意のE9完了条件を確認する
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 関連ファイル

- `pyproject.toml`
- `src/living_narrative/state/models.py`
- `src/living_narrative/plugins/sdk.py`(`PluginRuntime`、`PluginSDK`、`load_plugins`、`create_plugin_runtime`)
- `src/living_narrative/plugins/__init__.py`
- `src/living_narrative/llm/registry.py`
- `src/living_narrative/safety/registry.py`
- `src/living_narrative/narration/renderers.py`
- `src/living_narrative/narration/llm_narrator.py`(production配線: `registry`引数)
- `src/living_narrative/pipeline/registry.py`
- `src/living_narrative/pipeline/driver.py`(production配線: `TurnPipeline.run`が`create_plugin_runtime`で構築)
- `src/living_narrative/pipeline/llm_gateway.py`(production配線: `LLMGateway.runtime`)
- `src/living_narrative/cli/export.py`(production配線: `export images`が`runtime.create_image_provider`)
- `src/living_narrative/media/registry.py`
- `src/living_narrative/media/voice_registry.py`
- `docs/plugin-sdk.md`
- `docs/adr/0004-explicit-plugin-allowlist-trust-boundary.md`
- `tests/plugins/test_sdk.py`

## E9残条件の確認

Issue 049時点でE9(Productization)の5完了条件は次のとおりすべて`status: done`で揃っている。

- README起動: 048(Docker Compose + quickstart)
- backup/restore: 047(`living-narrative backup`/`restore` CLI)
- schema migration: 044(`schema_version` + migration骨格)
- plugin追加方法: 049本issue(`docs/plugin-sdk.md`)
- 権利・セキュリティ注意: 050(`docs/rights-and-security.md`)、および049のADR-0004(plugin信頼境界)

049は`038`(TRPGセッションモード)・`043`(voice/TTS export)へ依存していたが両方`done`済みで
着手した。長期安定運用(継続的な実運用フィードバック)は個別issueの範囲外の継続事項として
残るが、feature-dag(`docs/plan/feature-dag-e7-e9.md`)が定義するE9の完了条件自体は本issueの
完了をもってすべて揃った。
