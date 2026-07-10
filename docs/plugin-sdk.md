# Plugin SDK

Living Narrative Engineは、外部Python packageが既存の拡張レジストリへ登録するための
最小SDKを提供する。pluginは自動実行されず、`project.yaml`の`plugins` allowlistに
entry point名を明記した場合だけロード対象になる。

## 対応する拡張点

`PluginSDK`は次の6メソッドだけを公開する。

- `register_llm_provider(name, factory)`: `Provider` Protocolを返すfactory。
- `register_checker(name, checker)`: 既存checker callable。
- `register_renderer(name, renderer)`: `RendererFunc` callable。
- `register_pipeline_slot(name, slot)`: 既存pipeline slot実装。
- `register_image_provider(name, factory)`: `ImageProvider` Protocolを返すfactory。
- `register_voice_provider(name, factory)`: `VoiceProvider` Protocolを返すfactory。

現行`TurnPipeline`のphase/slot名は固定でbuilt-in名との衝突は拒否される。追加slot名は
将来またはprogrammatic consumer向けで、新phaseを作らない。現行voice機能もprompt/script
exportまでであり、voice factoryはprogrammatic/provider consumer向けでengine内TTS生成を
追加しない。

新しい操作/API経路は作られない。登録後もengineは既存の`session/mode.py`、
`_require_*`、`can_view_gm_vault`を含む権限境界の内側からレジストリを利用する。
各projectはbuilt-in registryのcloneから専用runtimeを作るため、あるprojectの登録は別projectや
module globalへ漏れない。空allowlistはbuilt-inだけの従来runtimeと同じ動作になる。

## package側の定義

外部packageは単一group `living_narrative.plugins`へ、登録関数または
`register(sdk)`を持つ宣言objectを公開する。

```toml
[project.entry-points."living_narrative.plugins"]
acme-story-tools = "acme_story_tools.plugin:register"
```

```python
def register(sdk):
    sdk.register_renderer("acme", render_acme)
```

entry point名（例では`acme-story-tools`）がallowlist照合キーであり、import pathや
package名ではない。

## 有効化

信頼できるpackageを明示的にinstallした後、project設定へentry point名を追加する。
既存projectは`plugins`省略時に空リストとなり、schema version 1のまま移行不要で読める。

```yaml
schema_version: 1
plugins:
  - acme-story-tools
```

発見処理はentry pointを列挙し、`name`をallowlistと照合してから、選択済みの項目だけに
`EntryPoint.load()`を呼ぶ。allowlist外のコードはimportも実行もされない。
同じ有効名が複数発見された場合は全候補をload前に曖昧性として拒否し、他の一意なpluginは
継続する。`living-narrative-noop`も明示allowlistなしにはloadされない。

## 失敗の扱い

`load_plugins()`は`PluginLoadResult`を返し、成功名を`loaded`、失敗を`errors`へ記録する。
失敗stageは`missing`（有効だが未install）、`load`（import/load失敗）、`register`
（登録失敗）のいずれかである。1 pluginの失敗後も他のpluginとengineは継続できる。
登録はplugin単位のtransactionである。登録先の名前がbuilt-inまたは先行pluginと衝突した
場合は`reason: collision`でplugin全体を拒否し、途中までの登録もrollbackする。登録後に
plugin codeが例外を投げた場合も同様に部分登録を残さず、後続pluginを処理する。
例外本文はsecret、path、API keyを含み得るためresult/logへ出さず、stage、reason、例外type
だけを安定した形式で報告する。

productionではruntimeがTurnPipeline（checker/rendererと固定slot）、LLMGateway（LLM
provider）、media export（image provider）へ渡される。追加slotとvoice factoryは同じ
project runtimeのprogrammatic surfaceで、project間では共有されない。

## 信頼境界

`EntryPoint.load()`は任意Pythonコードの実行である。pluginをsandbox化する仕組みは今回の
scopeに含まれないため、出所と内容を確認したpackageだけを明示的にinstall・有効化する。
自動発見したpluginを自動実行してはならず、API key、project data、filesystemへの通常の
Python process権限をpluginが持ち得る前提で運用する。
