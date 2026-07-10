# ADR-0004: pluginを明示allowlistで有効化する

## Context

外部packageから6種の既存レジストリを拡張したい。一方、Python entry pointのloadは任意
コード実行であり、単なる自動発見を実行許可として扱うと、projectを開くだけで未承認
コードが動く危険がある。企画書§11.5はsandbox化を将来要件として挙げるが、完全なPython
sandboxは今回の薄いSDK境界のscopeを大きく超える。

## Decision

- entry-point groupは`living_narrative.plugins`の1つだけとする。
- `ProjectConfig.plugins`をschema version 1のdefault空allowlistとして追加する。
- entry point列挙後、`EntryPoint.name`がallowlistにある項目だけをloadする。
- 同じ有効名が複数あればload前に曖昧性として拒否する。
- allowlist外pluginはload/import/実行しない。自動発見・自動実行は行わない。
- pluginには6種の既存レジストリへの登録面だけを渡し、新しい操作/API/権限経路は作らない。
- projectごとにbuilt-in registryをcloneし、登録済みruntimeをglobalや他projectと共有しない。
- plugin単位でstaging cloneへ登録し、名前衝突または例外時は全登録をrollbackする。built-inや
  先行pluginの名前は上書きできない。
- 未install、load失敗、登録失敗を構造化して報告し、他pluginとengineは継続する。
- 外部例外本文はresult/logへ出さず、stage・reason・例外typeだけを報告する。
- sandbox機構は今回実装しない。明示的にinstall・有効化した信頼済みpluginだけを使う。

## Consequences

旧projectは変更なしで読め、pluginの追加方法と実行条件は明確になる。利用者はplugin codeが
engine processと同じ権限で動く信頼境界を引き受ける。将来sandboxを導入する場合も、既存の
allowlistを第一段の許可判断として維持できる。
project-local cloneとtransactionには小さな生成costがあるが、project間汚染と部分登録状態を
防ぎ、空allowlistの従来動作を維持できる。
