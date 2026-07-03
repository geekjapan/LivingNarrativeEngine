# design.md — add-state-model

## Context

state-model は本プロジェクトで最も load-bearing な change である。以降の全 change
(random-engine, llm-provider, turn-pipeline, agent-runtime, intervention, session-autonomy, cli)は
ここで定義するモデル・StateStore・StateDiff を直接利用する。設計の誤りは全体に波及するため、
spec-foundation §5 / §5.1 の契約をそのままコードに落とし込み、拡張の余地(未知フィールド許容、
visibility の汎用化)を残しつつ、YAGNI に反する speculative generality は避ける。

## Goals

- spec-foundation §5 の全状態ファイルに対応する型安全な Pydantic v2 モデルを用意する。
- state 変更を必ず StateDiff 経由にする(D107)ための検証・適用・rollback の基盤を提供する。
- git diff がノイズなく読めるよう、保存時のキー順序を安定させる。
- ロード失敗時に「どのファイルのどのフィールドが壊れているか」を一括で報告する。

## Non-Goals

- Agent / pipeline / LLM 呼び出しとの統合(後続 change の責務)。
- Branch 管理・rollback CLI(データ操作のみ本 change の範囲)。
- unresolved_threads の自動検出・提案ロジック。

## Decisions

### D105(再確認): Pydantic v2 モデルをスキーマの単一正本にする

- **決定**: 全状態ファイル・Event・Intervention・StateDiff は Pydantic v2 の `BaseModel` として定義し、
  YAML はロード時に必ずこのモデルで検証する。JSON Schema はモデルから `model_json_schema()` で
  自動導出し、別途手書きしない。
- **理由**: 検証・構造化出力・ドキュメント生成を一元化できる(spec-foundation §2)。
- **代替案**: JSON Schema を正本にして Pydantic を後から生成 — 却下。Python コードとの結合が弱まり、
  IDE 補完・型チェックの恩恵を失う。

### 未知フィールドの扱い: 警告であって forbid ではない

- **決定**: 各モデルの `model_config` は `extra="allow"` とし、未知フィールドをロード後に走査して
  警告ログを出す(将来のスキーマ拡張に対する前方互換のため)。ただし既知フィールドの型・範囲検証は
  厳格に行う。
- **理由**: spec-foundation §5「未知フィールドは警告(forbid ではなく将来互換)」に明記されている。
- **代替案**: `extra="forbid"` — 却下(spec-foundation と矛盾)。`extra="ignore"` — 却下(黙って
  データを捨てるとユーザーの手書き YAML の typo に気づけない)。

### delta が範囲外になった場合: clamp して警告を記録する

- **決定**: `delta` op で 0-100 の数値フィールド(emotions, relationship の trust/affection/tension/
  suspicion, world parameters)が範囲外になる場合、エラーにせず 0 または 100 に clamp し、
  適用結果(apply report)に `clamped: true` と元の計算値を記録する。turn artifact の `checks.yaml` 等
  上位層がこれを見て警告表示するかは pipeline 側の責務とする。
- **理由**: LLM が生成する delta 値は厳密に範囲内である保証がない。感情や関係性のような値は
  「上限に張り付く」ことが物語上自然であり、ターン全体を reject するほどの異常ではない。
  一方で無警告の clamp はデバッグを困難にするため、apply report に記録して観測可能にする。
- **代替案**: エラーとして reject — 却下。LLM 出力のブレで頻発し、turn 失敗率が上がりすぎる。
  無条件 clamp(記録なし) — 却下。回帰時に「なぜ 100 で頭打ちなのか」を追えなくなる。

### dot-path のリスト解決: リストは id 一致、スカラーは直接置換

- **決定**: `path` がリストに到達する場合、要素が `id` フィールドを持つオブジェクトのリストなら
  「id 一致で対象要素を特定して add/remove/set」する。要素がスカラー(文字列等、例: knowledge.knows
  や secrets のような文字列リスト)の場合、`add` は末尾追加、`remove` は値の完全一致で削除、`set` は
  インデックス指定不可としリスト全体を置換する(`value` にリスト全体を渡す)。
- **理由**: canon エントリや relationship のように id を持つ要素は id 一致でないと「どの要素を消すか」
  が曖昧になる。一方 knowledge.knows のような自由記述の文字列リストには id がなく、値一致以外に
  安定した参照方法がない。
- **代替案**: 常にインデックス指定(`path: knowledge.knows[2]`) — 却下。LLM が生成する diff で
  インデックスは並行変更に弱く、順序がずれると誤った要素を消す。id/値一致の方が意図に忠実。

### 適用前状態の保存: turn 単位のスナップショット + inverse diff の併用

- **決定**: 各ターンの `state_diff.yaml` を保存すると同時に、そのターンで変更対象になった
  **ファイル単位の適用前スナップショット**(turn artifact 内、例: `runs/turn_0018/pre_state/`)を保存する。
  さらに `StateDiff` から機械的に導出できる `InverseStateDiff`(各 change の逆操作: `add`↔`remove`、
  `set` は旧値を保持して `set` に戻す、`delta` は符号反転)を `runs/turn_0018/inverse_diff.yaml` として
  併せて保存する。rollback はまず inverse diff の逆順適用を試み、diff 生成ロジックのバグ等で
  inverse 適用が失敗した場合のみ pre_state スナップショットへの復元にフォールバックする。
- **理由**: 純粋スナップショットのみだと変更のなかったファイルまで含め毎ターン全状態を複製すること
  になり、長時間セッションで artifact が肥大化する(spec-foundation は「1ターンあたりのファイル出力」
  を明示的な設計対象にしている§6)。一方 inverse diff のみだと diff→逆 diff 変換ロジックのバグが
  そのまま rollback の信頼性低下に直結する。両者を併用し、通常経路は軽量な inverse diff、
  安全網として変更ファイルのみのスナップショットを持つことで、肥大化と信頼性のトレードオフを両立する。
- **代替案**: 全ファイルの完全スナップショットのみ — 却下(肥大化)。inverse diff のみ — 却下
  (安全網がなく rollback 自体のバグがデータ破損に直結する)。両方省略し git 履歴で代替 — 却下
  (workspace が git 管理されている保証がなく、ターン単位の機械的 rollback にならない)。

### StateStore の保存: atomic write + 安定キー順序

- **決定**: 保存は「一時ファイルへ書き込み → `os.replace` でリネーム」で行い、書き込み途中のファイルを
  正本として見せない。YAML のキー順序は各モデルで定義したフィールド順(Pydantic のフィールド定義順)
  に固定し、`yaml.safe_dump(..., sort_keys=False)` で出力する。
- **理由**: atomic write はクラッシュ時の破損ファイルを防ぐ。安定キー順序は git diff を最小化し、
  レビュー容易性(spec-foundation の可観測性方針)を満たす。
- **代替案**: 都度 `sort_keys=True`(アルファベット順) — 却下。フィールドの論理的な並び(id → name →
  内容)が失われ、人間可読性が下がる。

### バリデーションエラーの集約

- **決定**: `StateStore.load()` は最初のエラーで例外送出せず、workspace 内の全対象ファイルを走査して
  発生した Pydantic `ValidationError` を `(file_path, field_path, message)` のリストとして集約し、
  1つの `StateLoadError` にまとめて送出する。
- **理由**: 大量の手書き YAML を one-by-one で直す体験を避ける。CLI/pipeline はエラー一覧を一括表示できる。
- **代替案**: fail-fast(最初のエラーで即停止) — 却下。修正→再実行のループが長くなる。

## Risks & Trade-offs

- [Risk] clamp による暗黙の値補正が、意図しない挙動(常に 100 に張り付く感情)を隠す。
  → Mitigation: apply report に `clamped` を必ず記録し、後続 change(checker)がこれを検査対象にできるようにする。
- [Risk] dot-path のリスト解決規則(id 一致 / 値一致)が複雑で実装・テストコストが上がる。
  → Mitigation: 対象パスの型(id を持つオブジェクトのリストかスカラーのリストか)は Pydantic モデルから
  静的に判定できるため、パスごとに一意の解決規則を決定でき、曖昧さは実行時に発生しない。
- [Risk] inverse diff とスナップショットの二重保存で artifact サイズが増える。
  → Mitigation: スナップショットは「そのターンで変更対象になったファイルのみ」に限定し、フル
  スナップショットにしない。

## Open Questions

- pre_state スナップショットの保持期間(全ターン恒久保存 vs 直近 N ターンのみ)は、export-replay /
  session-autonomy 側のディスク運用方針が固まってから決める(第1バッチはブロックしない)。
- unresolved_threads.yaml のスキーマは本 change で固定するが、他状態ファイルとの参照整合性チェック
  (例: canon entry が指す thread が実在するか)は Phase 5 の自動運用実装時に再検討する。
