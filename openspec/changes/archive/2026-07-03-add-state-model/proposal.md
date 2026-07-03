# add-state-model

## Why

物語エンジンの全コンポーネント(pipeline / agent / intervention / autonomy)は、状態ファイル
(world / character / scene / canon / reader_state / gm_vault 等)を同じ形で読み書きできる必要がある。
その共通スキーマと安全な変更手段(state diff)がなければ、後続の change はそれぞれ独自形式を実装してしまい、
情報スコープ分離(spec-foundation §4)や rollback(§5.1)を守れなくなる。

## What Changes

- state-model capability として、spec-foundation §5 に列挙された全状態ファイルに対応する Pydantic v2 モデルを追加する:
  `WorldState` / `FactionState` / `CharacterState` / `RelationshipState` / `SceneState` / `CanonEntry` /
  `ReaderStateEntry` / `GmVaultEntry` / `TimelineEntry` / `UnresolvedThread`。
- `Visibility` enum(`gm_only` / `canon` / `character` / `scene` / `reader`)を追加し、Event・Fact・
  Intervention・StateDiffChange から共通利用できるようにする。
- `Event` モデル(id/turn/type/cause/visibility/known_by/hidden_from/effects)を追加する。
- ID 検証(spec-foundation §3 の `<type>_<zero-padded番号>` 規約)を共通バリデータとして追加する。
- workspace 全体の状態ファイルを型付きでロードする `WorldStateBundle` と `StateStore`
  (load / save / atomic write / stable key order / aggregated validation errors / unknown-field warning)を追加する。
- `StateDiff` モデルと diff 適用エンジン(spec-foundation §5.1 準拠: add/remove/set/delta、dot-path、
  visibility、source_event、ターン単位アトミック適用、reject 時状態不変、partial apply)を追加する。
- diff 適用時に inverse diff を生成・保存し、rollback(逆順再適用)に使えるデータ操作を追加する。

## Capabilities

### New Capabilities

- `state-model`: 全状態ファイルの Pydantic スキーマ、情報スコープ用 Visibility、ID 検証、
  StateStore によるロード/保存、StateDiff の検証・適用・rollback。

### Modified Capabilities

(none)

## Non-Goals

- Agent Runtime(Context Builder / Character Agent / World Simulator / Conflict Resolver)は対象外。
- Turn pipeline のフェーズ実装は対象外(state-model はそのための基盤のみを提供する)。
- Memory summary・foreshadowing ledger は対象外(Phase 5)。
- Branch 管理の UI・CLI コマンドは対象外(データ形式のみ本 change で固定し、運用は後続 change)。
- rollback の CLI/UX(コマンド、確認プロンプト等)は対象外。本 change は逆 diff 適用というデータ操作のみを提供する。
- unresolved_threads の自動運用(検出・提案)は対象外(第1バッチではデータ形式のみ)。

## Dependencies

- `add-project-foundation`(project.yaml のロードと workspace レイアウトが前提)。

## Impact

- 新規パッケージ `living_narrative.state` を追加(models / store / diff / rollback のサブモジュール)。
- 新規依存追加なし(pydantic v2 / PyYAML は spec-foundation §2 で確定済み)。
- 後続の全 change(random-engine 以降)はここで定義するモデル・StateStore・StateDiff を利用する。
