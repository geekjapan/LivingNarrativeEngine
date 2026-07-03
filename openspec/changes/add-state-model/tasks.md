## 1. 共通基盤

- [ ] 1.1 `living_narrative/state/` パッケージを新設し、`ids.py` に spec-foundation §3 の
      `<type>_<zero-padded番号>` を検証する共通バリデータ(Pydantic `AfterValidator` or
      `field_validator`)を実装する(プレフィックスは型ごとに明示指定するファクトリ関数とし、
      `character`→`char`、`intervention`→`int`、`unresolved_threads`→`thread`、それ以外は型名を
      そのまま使用する。数字部分は3桁以上のゼロ埋めとし桁数上限は設けない。`fact` プレフィックスも
      対象に含める)
- [ ] 1.1b `target: relationship` の `StateDiffChange.id` 用に、有向複合キー
      `<from_id>__<to_id>`(D116。`from_id`/`to_id` それぞれが有効な character id)を検証する
      専用バリデータを実装する
- [ ] 1.2 `Visibility` enum(`gm_only`/`canon`/`character`/`scene`/`reader`)を
      `models/visibility.py` に実装する
- [ ] 1.3 0-100 整数フィールド用の共通型(`Percent = Annotated[int, Field(ge=0, le=100)]`)を実装する

## 2. 状態モデル

- [ ] 2.1 `WorldState` / `FactionState`(parameters/resources/relations、Percent 適用)を実装する
- [ ] 2.2 `CharacterState`(traits/goals/emotions/knowledge/secrets/private_mind/inventory/
      constraints/status: `alive`|`dead`|`missing` 既定 `alive`、D123)を実装する
- [ ] 2.3 `RelationshipState`(from/to/trust/affection/tension/suspicion/notes、自己参照禁止
      バリデーション)を実装する
- [ ] 2.4 `HiddenFact`(id=`fact_NNN`/text/visibility/known_by、D115)と `SceneState`
      (active_characters/reader_visible_facts: `list[str]`/hidden_facts: `list[HiddenFact]`/
      status: `active`|`ended` 既定 `active`、D123)を実装する
- [ ] 2.5 `CanonEntry` / `ReaderStateEntry` / `GmVaultEntry` を実装する
- [ ] 2.6 `TimelineEntry` / `UnresolvedThread`(データ形式のみ)を実装する
- [ ] 2.7 `Event`(known_by/hidden_from の矛盾禁止バリデーション、省略可能な `roll_ids: list[str]`
      (D121、既定空リスト)を含む)を実装する
- [ ] 2.8 `WorldStateBundle`(上記全モデルを束ねるコンテナ)を実装する

## 3. StateStore(ロード/保存)

- [ ] 3.1 `store.py` に `StateStore.load(workspace_path) -> WorldStateBundle` を実装する
      (固定7ファイル(world/canon/reader_state/gm_vault/relationships/timeline/
      unresolved_threads)の欠落は `StateLoadError` で fail-fast、D117。固定ファイルが存在し
      空の場合は空コレクション。`characters/`/`scenes/` ディレクトリの欠落は従来通り空コレクション
      扱いのまま lenient)
- [ ] 3.2 バリデーションエラー集約(`StateLoadError`: file_path/field_path/message のリスト)を実装する
- [ ] 3.3 未知フィールド検出・警告ロギング(`extra="allow"` + 走査)を実装する
- [ ] 3.4 `StateStore.save(bundle, workspace_path)` を実装する
      (一時ファイル書き込み → `os.replace`、`sort_keys=False` によるフィールド定義順出力)

## 4. StateDiff エンジン

- [ ] 4.1 `diff.py` に `StateDiffChange` / `StateDiff`(spec-foundation §5.1 準拠)を実装する
- [ ] 4.2 dot-path 解決器(スカラー直接置換 / id 一致リスト解決)を実装する
- [ ] 4.3 適用前検証(target 存在確認、path 解決可能性、delta は数値フィールドのみ)を実装する
- [ ] 4.4 適用エンジン(add/remove/set/delta)をアトミックに実装する
      (1件でも失敗したら全体 reject、状態不変を保証。id 一致リストへの `remove` が対象不在の
      場合も同じ適用時エラーとして扱い、事前存在確認バリデーションフェーズは設けない。
      Q3 recommendation B)
- [ ] 4.5 0-100 clamp とその apply report への記録を実装する
- [ ] 4.6 partial apply(changes の部分集合選択適用)を実装する

## 5. Rollback

- [ ] 5.1 `InverseStateDiff` 生成ロジック(add↔remove、set は旧値保持、delta は符号反転)を実装する
      (id 一致リストへの `remove` は `value` 省略可能とし、適用前状態からフル内容を読み取って
      inverse の `add.value` に格納する。Q3 recommendation B)
- [ ] 5.2 適用結果と `InverseStateDiff` の保存(turn artifact 想定パスへの書き出し関数)を実装する
- [ ] 5.3 ターン範囲 N..M の逆順適用による rollback データ操作関数を実装する

## 6. テスト(pytest, mock provider 不要・純粋ユニット)

- [ ] 6.1 各状態モデルの正常系・異常系(範囲外値、ID フォーマット不正、必須フィールド欠落、
      `CharacterState.status`/`SceneState.status` の既定値・enum 外の値の拒否、D123)を
      テストする
- [ ] 6.2 `StateStore` の roundtrip テスト(save→load で内容一致、保存出力バイト列の再現性)を書く
- [ ] 6.3 `StateStore` の固定ファイル欠落時の fail-fast(`StateLoadError`)、固定ファイルが空の場合の
      成功、可変コレクションディレクトリ欠落時の lenient な成功、未知フィールド警告、複数エラー集約を
      テストする
- [ ] 6.4 `StateDiff` の適用成功・reject(部分失敗時の状態不変・id 一致 remove の対象不在時 reject 含む)・
      partial apply をテストする(`op: set, path: status` による `CharacterState.status`→`dead`・
      `SceneState.status`→`ended` の遷移を含む、D123)
- [ ] 6.5 delta clamp のテスト(上限超過・下限超過それぞれ)を書く
- [ ] 6.6 inverse diff の生成と、生成した inverse diff を適用して元の状態に戻ることを確認する
      roundtrip テストを書く(`value` 省略の id 一致 remove から pre-state 由来の add.value を持つ
      inverse が生成されるケースを含む)
- [ ] 6.7 複数ターンの rollback(3ターン分の inverse diff を逆順適用)テストを書く

## 7. ドキュメント

- [ ] 7.1 `model_json_schema()` から全モデルの JSON Schema をエクスポートするスクリプト/コマンドを
      追加する
- [ ] 7.2 `docs/state-model.md`(または同等の場所)に状態ファイル一覧・StateDiff 記法・
      rollback の仕組みを、spec-foundation を参照しつつ簡潔にまとめる
