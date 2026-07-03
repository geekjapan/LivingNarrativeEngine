# state-model spec

## ADDED Requirements

### Requirement: ID フォーマット検証
全 ID フィールド(world/faction/character/scene/canon/reader_state/gm_vault/timeline/unresolved_threads/event/intervention/roll/diff の id)は spec-foundation §3 の `<type>_<zero-padded番号>` 規約に一致しなければならない(SHALL)。一致しない値でモデルを構築した場合、`ValidationError` を送出しなければならない(SHALL)。

#### Scenario: 正しい形式の ID
- **WHEN** `char_001` のような `<type>_<zero-padded番号>` 形式の id で `CharacterState` を構築する
- **THEN** バリデーションが成功し、モデルが構築される

#### Scenario: 不正な形式の ID
- **WHEN** `char1` や `CHAR_001` のような規約に一致しない id で状態モデルを構築する
- **THEN** `ValidationError` が送出され、モデルは構築されない

### Requirement: World / Faction モデル
`WorldState` は id/name/summary/laws(文字列リスト)/parameters を持たなければならない(SHALL)。`parameters` の各値は 0 以上 100 以下の整数でなければならない(SHALL)。`FactionState` は id/name/public_face/goals/resources/relations(faction_id をキーとする hostility 等の数値)を持たなければならない(SHALL)。

#### Scenario: parameters が範囲内
- **WHEN** `danger_level: 40` のように 0-100 の整数で `WorldState.parameters` を構築する
- **THEN** バリデーションが成功する

#### Scenario: parameters が範囲外
- **WHEN** `danger_level: 140` のように 100 を超える値で `WorldState.parameters` を構築する
- **THEN** `ValidationError` が送出される

### Requirement: Character モデル
`CharacterState` は id/name/role/traits/goals(short_term/long_term)/emotions(0-100 整数の辞書)/knowledge(knows/believes/does_not_know の3リスト)/secrets/private_mind/inventory/constraints を持たなければならない(SHALL)。`private_mind` は情報スコープ上「本人のみ可視」(spec-foundation §4.1)であることをモデルのドキュメント文字列に明記しなければならない(SHALL)。

#### Scenario: 完全な CharacterState の構築
- **WHEN** 企画書 §14.4 の例に相当する全フィールドを持つ YAML から `CharacterState` を構築する
- **THEN** バリデーションが成功し、`knowledge.knows` / `knowledge.believes` / `knowledge.does_not_know` がそれぞれ独立したリストとして保持される

#### Scenario: emotions が範囲外
- **WHEN** `emotions.fear: -5` のように負の値で `CharacterState` を構築する
- **THEN** `ValidationError` が送出される

### Requirement: Relationship モデル
`RelationshipState` は有向ペア(`from`/`to` に character id)と trust/affection/tension/suspicion(いずれも 0-100 整数)、notes(文字列リスト)を持たなければならない(SHALL)。`from` と `to` が同一 character id の場合、`ValidationError` を送出しなければならない(SHALL)。

#### Scenario: 有効な relationship の構築
- **WHEN** `from: char_001, to: char_002, trust: 62, affection: 40, tension: 25, suspicion: 35` で `RelationshipState` を構築する
- **THEN** バリデーションが成功する

#### Scenario: from と to が同一
- **WHEN** `from` と `to` が同じ character id である `RelationshipState` を構築する
- **THEN** `ValidationError` が送出される(自己参照の関係性は不正とする)

### Requirement: Scene モデル
`SceneState` は id/location/time/active_characters(character id リスト)/mood/stakes/reader_visible_facts/hidden_facts を持たなければならない(SHALL)。`reader_visible_facts` と `hidden_facts` は spec-foundation §4.1 の Scene スコープに従い別フィールドとして分離しなければならない(SHALL)。

#### Scenario: Scene の構築
- **WHEN** 企画書 §14.6 の例に相当する YAML から `SceneState` を構築する
- **THEN** バリデーションが成功し、`reader_visible_facts` と `hidden_facts` が別リストとして保持される

### Requirement: Canon / Reader State / GM Vault エントリモデル
`CanonEntry` は id/text/established_turn/source_event を持たなければならない(SHALL)。`ReaderStateEntry` は `CanonEntry` と同じフィールドに加え開示ターン(`disclosed_turn`)を持たなければならない(SHALL)。`GmVaultEntry` は id/text/`reveal_condition`(省略可能)を持たなければならない(SHALL)。

#### Scenario: GmVaultEntry の reveal_condition 省略
- **WHEN** `reveal_condition` を指定せず `GmVaultEntry` を構築する
- **THEN** バリデーションが成功し、`reveal_condition` は `None` になる

#### Scenario: CanonEntry の必須フィールド欠落
- **WHEN** `established_turn` を指定せず `CanonEntry` を構築する
- **THEN** `ValidationError` が送出される

### Requirement: Timeline / Unresolved Threads モデル
`TimelineEntry` はターン番号(`turn`)と当該ターンで発生した event id のリストを持たなければならない(SHALL)。`UnresolvedThread` は id/description/status/related_event_ids のデータ形式を定義しなければならない(SHALL)。本 change は `UnresolvedThread` の自動検出・自動解決ロジックを実装してはならない(MUST NOT)。

#### Scenario: TimelineEntry の構築
- **WHEN** `turn: 18, event_ids: [event_0081, event_0082]` で `TimelineEntry` を構築する
- **THEN** バリデーションが成功する

### Requirement: Visibility enum
`Visibility` enum は `gm_only` / `canon` / `character` / `scene` / `reader` の5値を持たなければならない(SHALL)。`Event` / 状態エントリ(canon/gm_vault 等の可視性を持ちうるフィールド)/ `StateDiffChange` は `visibility: Visibility` フィールドで参照しなければならない(SHALL)。`visibility` が `character` の場合、`known_by`(character id リスト)を伴えなければならない(SHALL)。詳細な情報スコープの意味論は spec-foundation §4 に従う。

#### Scenario: character visibility に known_by を付与
- **WHEN** `visibility: character, known_by: [char_002]` を持つ `Event` を構築する
- **THEN** バリデーションが成功する

#### Scenario: 不正な visibility 値
- **WHEN** `visibility: everyone` のような enum 外の値で `Event` を構築する
- **THEN** `ValidationError` が送出される

### Requirement: Event モデル
`Event` は企画書 §14.7 に対応する id/turn/type/cause/visibility/known_by/hidden_from/effects を持たなければならない(SHALL)。`known_by` と `hidden_from` は同一 character id を同時に含んではならない(SHALL)。

#### Scenario: Event の構築
- **WHEN** 企画書 §14.7 の例に相当する YAML から `Event` を構築する
- **THEN** バリデーションが成功する

#### Scenario: known_by と hidden_from の矛盾
- **WHEN** 同一の character id が `known_by` と `hidden_from` の両方に含まれる `Event` を構築する
- **THEN** `ValidationError` が送出される

### Requirement: WorldStateBundle による workspace 全体ロード
`StateStore.load(workspace_path)` は workspace 内の全状態ファイル(project 設定を除く spec-foundation §5 記載の全ファイル)を読み込み、単一の型付き `WorldStateBundle` を返さなければならない(SHALL)。存在しない任意ファイル(例: `gm_vault.yaml` が未作成)は空コレクションとして扱わなければならない(SHALL)。

#### Scenario: 完全な workspace のロード
- **WHEN** world/characters/scenes/relationships/canon/reader_state/gm_vault/timeline/unresolved_threads の各ファイルが揃った workspace を `StateStore.load()` に渡す
- **THEN** 全フィールドが対応するモデルとして格納された `WorldStateBundle` が返る

#### Scenario: 任意ファイルの欠落
- **WHEN** `gm_vault.yaml` が存在しない workspace を `StateStore.load()` に渡す
- **THEN** ロードは成功し、`WorldStateBundle.gm_vault` は空リストになる

### Requirement: バリデーションエラーの集約
`StateStore.load()` は workspace 内の複数ファイルで検証エラーが発生した場合、最初のエラーで中断せず全ファイルを走査し、各エラーをファイルパスとフィールドパスを含む形で集約した単一の `StateLoadError` として送出しなければならない(SHALL)。

#### Scenario: 複数ファイルでの検証エラー
- **WHEN** `characters/char_001.yaml` の emotions と `scenes/scene_001.yaml` の active_characters の双方に不正な値がある workspace をロードする
- **THEN** `StateLoadError` が送出され、両ファイルのパスとフィールドパスを含むエラー一覧が含まれる

### Requirement: 未知フィールドの警告
状態ファイルに定義済みモデルに存在しないフィールドが含まれる場合、`StateStore.load()` はロードを失敗させてはならず(MUST NOT)、当該ファイルパスとフィールド名を含む警告を発生させなければならない(SHALL)。

#### Scenario: 未知フィールドを含む YAML のロード
- **WHEN** `CharacterState` に定義されていない `favorite_color` フィールドを含む `characters/char_001.yaml` をロードする
- **THEN** ロードは成功し、`char_001.yaml` と `favorite_color` を含む警告が記録される

### Requirement: 保存時の atomic write と安定キー順序
`StateStore.save()` は保存対象ファイルごとに一時ファイルへ書き込んだ後にリネームすることで書き込みを原子的に行わなければならない(SHALL)。YAML 出力のキー順序はモデルのフィールド定義順に固定し、同一データを複数回保存した場合に出力バイト列が一致しなければならない(SHALL)。

#### Scenario: 保存の原子性
- **WHEN** `StateStore.save()` の実行中にプロセスが強制終了したと仮定する
- **THEN** 保存対象ファイルは書き込み前の内容のまま残るか、書き込み後の内容に完全に置き換わっているかのいずれかであり、部分的に書き込まれた壊れたファイルにはならない

#### Scenario: 保存出力の再現性
- **WHEN** 同一の `WorldStateBundle` を2回連続で `StateStore.save()` する
- **THEN** 生成される YAML ファイルのバイト列は2回とも完全に一致する

### Requirement: StateDiff モデルと dot-path 検証
`StateDiff` は spec-foundation §5.1 の形式(id/turn/changes[]、各 change は target/id?/op/path/value/visibility/source_event)に従わなければならない(SHALL)。適用前検証として、`op: delta` は数値フィールドに対してのみ許可されなければならず(SHALL)、`path` は対象モデルのフィールド階層として解決可能でなければならない(SHALL)。解決できない `path` を持つ change は検証エラーとしなければならない(SHALL)。

#### Scenario: 妥当な StateDiff の検証
- **WHEN** spec-foundation §5.1 の例に相当する `StateDiff` を対象 `WorldStateBundle` に対して検証する
- **THEN** 検証が成功する

#### Scenario: 数値以外への delta
- **WHEN** `op: delta, path: name` のように文字列フィールドへ `delta` を指定した change を検証する
- **THEN** 検証エラーとなる

#### Scenario: 解決不能な path
- **WHEN** `path: nonexistent.field` のように対象モデルに存在しないパスを指定した change を検証する
- **THEN** 検証エラーとなる

### Requirement: StateDiff の適用(アトミック / reject 時状態不変)
`StateDiff` の適用は1ターン分の `changes` 全体を単位としてアトミックに行われなければならない(SHALL)。いずれか1つの change が適用時エラー(対象不在・型不一致等)になった場合、適用済みの変更を含め全ての変更を巻き戻し、適用前の状態を完全に保持しなければならない(SHALL)。

#### Scenario: 全 change が成功
- **WHEN** 全 change が有効な `StateDiff` を `WorldStateBundle` に適用する
- **THEN** 全ての変更が反映された新しい `WorldStateBundle` が返る

#### Scenario: 一部の change が失敗
- **WHEN** 3件の change のうち1件が存在しない character id を対象にした `StateDiff` を適用する
- **THEN** 適用は reject され、`WorldStateBundle` は適用前と完全に一致する状態を保つ

### Requirement: delta の 0-100 clamp
0-100 範囲を持つ数値フィールド(emotions / relationship の trust・affection・tension・suspicion / world parameters)への `delta` 適用結果が範囲外になる場合、値を 0 または 100 に clamp しなければならない(SHALL)。この場合、適用結果(apply report)に元の計算値と clamp が発生した旨を記録しなければならない(SHALL)。

#### Scenario: 上限を超える delta
- **WHEN** 現在値 95 の `emotions.fear` に `delta: +20` を適用する
- **THEN** 結果は 100 に clamp され、apply report に `clamped: true` と計算値 115 が記録される

#### Scenario: 下限を下回る delta
- **WHEN** 現在値 10 の `relationship.trust` に `delta: -30` を適用する
- **THEN** 結果は 0 に clamp され、apply report に `clamped: true` と計算値 -20 が記録される

### Requirement: partial apply
`StateDiff.changes` の部分集合を選択して適用する partial apply をサポートしなければならない(SHALL)。選択されなかった change は状態に一切反映されず、選択された change のみがアトミック(本 spec の「StateDiff の適用」要件と同じ意味論)に適用されなければならない(SHALL)。

#### Scenario: 一部 change のみ選択して適用
- **WHEN** 3件の change を持つ `StateDiff` から2件のみを選択して適用する
- **THEN** 選択された2件のみが状態に反映され、残り1件に対応する変更は反映されない

### Requirement: inverse diff の生成と保存
`StateDiff` の適用時、各 change の逆操作(`add`↔`remove`、`set` は適用前の値を保持して `set` に戻す、`delta` は符号反転)からなる `InverseStateDiff` を生成し、適用結果とともに保存しなければならない(SHALL)。

#### Scenario: add change の逆操作
- **WHEN** `op: add, path: knowledge.knows, value: "新事実"` を含む `StateDiff` を適用する
- **THEN** 生成される `InverseStateDiff` は同じ path に対する `op: remove, value: "新事実"` を含む

#### Scenario: delta change の逆操作
- **WHEN** `op: delta, path: emotions.fear, value: 15` を含む `StateDiff` を適用する
- **THEN** 生成される `InverseStateDiff` は同じ path に対する `op: delta, value: -15` を含む

### Requirement: rollback(逆 diff の逆順適用)
複数ターン分の rollback は、対象ターン範囲(N..M)の `InverseStateDiff` をターン降順(M, M-1, ..., N)に順次適用することで実現されなければならない(SHALL)。rollback の対象データ操作自体は本 change の範囲とし、rollback を起動する CLI/UX は対象外とする。

#### Scenario: 複数ターンの rollback
- **WHEN** turn 16, 17, 18 の `InverseStateDiff` を、この順で保存された状態に対してターン 18, 17, 16 の順に適用する
- **THEN** 結果の状態は turn 15 終了時点の状態と一致する
