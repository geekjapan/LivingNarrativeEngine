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

### ID のプレフィックスと桁数のゼロ埋め規約

- **決定**: 共通 ID バリデータはプレフィックス文字列を型ごとに明示指定するファクトリ関数
  (`make_id_validator(prefix: str)` 相当)とする。プレフィックスは spec-foundation §3 の例に
  合わせ、`character`→`char`、`intervention`→`int`、`unresolved_threads`→`thread` の3型のみ
  短縮し、それ以外(`world`/`faction`/`scene`/`canon`/`reader_state`/`gm_vault`/`event`/`roll`/
  `diff`)は型トークンをそのままプレフィックスとする。数字部分は3桁以上のゼロ埋め(正規表現
  `^{prefix}_\d{3,}$`)とし、型ごとの桁数上限は設けない(char_001 のような3桁例と event_0001 の
  ような4桁例が spec-foundation §3 に混在するが、どちらも「3桁以上」で包含できる)。
  `TimelineEntry` は `turn`(整数)で一意なため id フィールド自体を持たず、このバリデータの対象外
  とする。
- **理由**: spec-foundation §3 は型ごとの厳密な桁数上限を規定しておらず、`canon`/`reader_state`/
  `gm_vault` のプレフィックス文字列も例示されていない。厳密な桁数固定(例: 全て3桁)は将来
  インスタンス数が桁数を超えた際に破壊的変更になるため、「3桁以上」という緩い制約で
  spec-foundation の全既知例と両立させる。プレフィックス文字列は spec-foundation §3 の ID
  フォーマット Requirement 自身が列挙する型トークン(canon/reader_state/gm_vault など)を
  そのまま採用し、恣意的な新規略語を発明しない。
- **代替案**: 型ごとに固定桁数(3桁 or 4桁)を割り当てる — 却下。`canon`/`reader_state`/
  `gm_vault` については spec-foundation に根拠となる例が無く、恣意的な決定になる。

### 未知フィールドの扱い: 警告であって forbid ではない

- **決定**: 各モデルの `model_config` は `extra="allow"` とし、未知フィールドをロード後に走査して
  警告ログを出す(将来のスキーマ拡張に対する前方互換のため)。ただし既知フィールドの型・範囲検証は
  厳格に行う。
- **理由**: spec-foundation §5「未知フィールドは警告(forbid ではなく将来互換)」に明記されている。
- **代替案**: `extra="forbid"` — 却下(spec-foundation と矛盾)。`extra="ignore"` — 却下(黙って
  データを捨てるとユーザーの手書き YAML の typo に気づけない)。

### delta が範囲外になった場合: clamp して警告を記録する

- **決定**: `delta` op で 0-100 の数値フィールド(emotions, relationship の trust/affection/tension/
  suspicion, world parameters, faction の resources/relations)が範囲外になる場合、エラーにせず
  0 または 100 に clamp し、
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

### CanonEntry / GmVaultEntry / ReaderStateEntry は visibility フィールドを持たない

- **決定**: `CanonEntry`・`GmVaultEntry`・`ReaderStateEntry` はモデル自身に `visibility` フィールドを
  追加しない。可視性はそれぞれが所属するファイル(`canon.yaml`→`canon`、`gm_vault.yaml`→`gm_only`、
  `reader_state.yaml`→`reader`)によって一意に決まる固定値として扱う。
- **理由**: この3ファイルはファイル自体が単一スコープの正本であり、エントリごとに異なる visibility を
  持たせる必要がない。`Event` と `StateDiffChange` のみがキャラクター単位の知識差(`known_by`)を
  表現する必要があるため `visibility` フィールドを持つ。
- **代替案**: 3モデルにも `visibility: Visibility` を追加する — 却下。常に固定値になり冗長。

### CharacterState の自由記述フィールドの型

- **決定**: `traits` / `secrets` / `private_mind` / `inventory` はいずれも `list[str]` とする。
  `constraints` は `dict[str, Any]` とする(Intervention の `constraints`(キー・バリューの追加制約)
  と同じ形にそろえる)。
- **理由**: 企画書 §14.4 の例は traits/goals/secrets のみを示し、private_mind/inventory/constraints
  の型を示さない。既存の同種フィールド(secrets)と対称にすることで恣意性を減らし、`extra="allow"`
  により将来より構造化された型へ移行する余地も残す(YAGNI: 現時点でアイテムオブジェクト等の
  構造化は導入しない)。
- **代替案**: inventory をアイテムオブジェクトのリスト(name/description/quantity)にする — 却下
  (現時点でどの change もこの構造を必要としておらず speculative generality)。

### GmVaultEntry.reveal_condition は自由記述文字列

- **決定**: `reveal_condition` は自由記述の `str | None` とし、本 change ではこの内容をプログラムで
  自動評価するロジックを実装しない。
- **理由**: 開示条件の自動判定(構造化条件式のパース・評価)はどの consumer change (add-intervention 等)
  にも要件として存在せず、第1バッチは GM の目視判断のみを前提とする。

### StateStore.save() のアトミック性はファイル単位であり、bundle 全体を横断しない

- **決定**: 「一時ファイル書き込み → `os.replace`」によるアトミック性は各ファイル単体の保証であり、
  `WorldStateBundle` 全体(複数ファイル)を1トランザクションとして保証するものではない。保存処理が
  複数ファイルの途中でクラッシュした場合、一部のファイルのみ新内容に更新された状態になり得る。
- **理由**: ファイル横断のトランザクション(ステージングディレクトリ + 一括スワップ等)は実装コストが
  高く、spec-foundation にもそのような要求はない。個々のファイルが常に「完全に書き込み前」か
  「完全に書き込み後」であることさえ保証されれば、壊れた(部分的に書き込まれた)YAML を読み込む
  事故は防げる。
- **代替案**: workspace 全体をステージングディレクトリに書いてから一括リネーム — 却下(YAGNI、
  第1バッチでクラッシュ耐性としてそこまでの粒度は要求されていない)。

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

### D116: RelationshipState は独自 id を持たず、複合キー `<from_id>__<to_id>` で特定する

- **決定**: `RelationshipState` に新規 id フィールドは追加しない。`target: relationship` を持つ
  `StateDiffChange`(および `add-intervention` の Intervention)は `id` フィールドに有向複合キー
  `<from_id>__<to_id>`(例 `char_001__char_002`)を格納し、これを対象特定手段として正式採用する。
  ID フォーマット検証はこの複合キーを `<type>_<zero-padded番号>` 規約の明示的な例外として扱い、
  `from_id`/`to_id` それぞれが単独で有効な character id であることを検証する。
- **理由**: grill Q1 で検討した3案(新規 sequential id / 複合キー文字列の許容 / target 別スキーマ分岐)
  のうち、from/to が自然キーとして既に一意性を持つため複合キーが最小の追加で済み、かつ
  StateDiffChange のスキーマを target ごとに分岐させずに済む。spec-foundation §3 がこの例外を
  正式に明文化した(D116)ことで、本 change 単独の決定ではなく横断契約として確定した。
- **代替案**: `rel_001` のような新規 sequential id を追加する — 却下(from/to が既に一意なペアである
  以上、冗長な二重 id を導入するリスクの方が大きい。grill Q1 選択肢 A)。

### D115: SceneState.hidden_facts を HiddenFact の構造化リストにする

- **決定**: `hidden_facts` を `list[str]` から `HiddenFact`(id=`fact_NNN`/text/visibility: `Visibility`/
  known_by: character id リスト)のリストへ変更する。`reader_visible_facts` は `list[str]` のまま
  変更しない。`hidden_facts` への dot-path add/remove/set は、他の id 付きオブジェクトのリスト
  (canon エントリ等)と同じ「id 一致」規則に従う。
- **理由**: grill Q2 で指摘した通り、spec-foundation §4.1「hidden はスコープ指定に従う」と
  add-agent-runtime の「本人が見てよい hidden_facts」というキャラクター単位フィルタリング要求は、
  fact ごとの visibility/known_by が無いと実装不能である。`Event` に既に存在する
  `visibility`/`known_by` の形をそのまま流用することで、モデル設計の一貫性も保てる。
- **代替案**: `list[str]` のまま維持し「シーン参加者全員に一律可視」と簡易解釈する — 却下
  (grill Q2 選択肢 B。spec-foundation §4.1 の「スコープ指定に従う」という記述と整合しない)。

### D117: 固定7ファイルの欠落は fail-fast、可変コレクションは lenient のまま

- **決定**: `StateStore.load()` は固定7ファイル(world/canon/reader_state/gm_vault/relationships/
  timeline/unresolved_threads)のいずれかが存在しない場合、「バリデーションエラーの集約」と同じ
  `StateLoadError` として fail-fast で失敗する。固定7ファイルが存在するがコレクションが空である
  場合は成功とし、対応するフィールドは空コレクションになる。`characters/`・`scenes/` のような
  可変数ディレクトリは、ディレクトリ自体が存在しない場合でも従来通り空コレクションとして
  ロードを成功させる(lenient のまま変更しない)。
- **理由**: add-project-foundation の init は固定7ファイルを必ず生成する契約になっており、
  その前提が破られている状態(欠落)は「壊れた workspace」であって「意図的に空」ではない。
  spec-foundation の「黙って握り潰さない」原則に従い、これを空コレクションとして黙って
  ロード成功させるのではなく明示的なエラーとして報告する。一方 `characters/`/`scenes/` は
  シーンやキャラクターが1件も存在しないプロジェクト初期状態が正当にあり得るため、
  ディレクトリ欠落を許容する現状の lenient な扱いを変える理由がない。
- **代替案**: 全ファイル(固定・可変とも)を lenient のまま維持する(旧決定) — 却下(D117。
  固定ファイルの欠落を検出できず、破損 workspace を静かに「空」として扱ってしまう)。
  全ファイルを fail-fast にする — 却下(`characters/`/`scenes/` が空のプロジェクトを起動できなく
  なり、YAGNI に反する過剰な制約になる)。

### D121: Event.roll_ids で roll の可視性を event 経由で導出する

- **決定**: `Event` に省略可能な `roll_ids: list[str]`(既定 空リスト)を追加する。roll 自体には
  visibility フィールドを持たせない。export-replay は「reader 可視な Event が参照する roll_ids」
  から roll の可視性を導出する契約とし、この導出ロジック自体の実装は本 change の範囲外とする。
- **理由**: Conflict Resolver は検出した衝突を例外なく roll で解決する設計(D121)であり、
  ある roll がどのイベントの結果として使われたかを追跡できないと、export-replay がどの roll を
  reader 向けに表示してよいか判断できない。roll 自体に visibility を持たせる案は roll と
  event の間に重複した可視性表現を生むため避けた。
- **代替案**: `Roll` モデルに直接 `visibility` を追加する — 却下(roll は本来イベントの副産物であり、
  可視性の正本を event 側に一本化した方がモデルの二重管理を避けられる)。

### remove-on-absent は適用時エラー、inverse の add.value は pre-state から取得(Q3 recommendation B)

- **決定**: id 一致で解決するリスト要素に対する `remove` change が指定した id/値が適用直前の状態に
  存在しない場合、これを検出するための独立した事前存在確認バリデーションフェーズは設けない。
  代わりに「StateDiff の適用」要件が定める既存のアトミック reject 経路(対象不在・型不一致等と
  同列の適用時エラー)でまとめて扱う。また、id 一致リストに対する `remove` change は
  `StateDiffChange.value` を省略できるものとし、この場合、適用エンジンは適用直前の状態
  (pre-state)から削除対象要素のフル内容を読み取り、生成する `InverseStateDiff` の対応する
  `add` change の `value` に格納する。
- **理由**: grill Q3 で検討した3案(A: 事前存在確認バリデーションフェーズを追加 / B: 既存の
  apply-time reject 経路に統合 / C: no-op として黙って許容)のうち、C は D107(state 変更は
  全て diff 経由・監査可能性)の趣旨に反し LLM の誤った diff を検出できなくなるため却下。
  A は「path 解決可能性」検証とは別に、apply 時点の current state 全体を都度スキャンする
  追加コストと新規バリデーションフェーズを生む。B は既存の「1つでも適用時エラーがあれば全体
  reject」という機構をそのまま再利用でき、新規の検証ステップを増やさない。inverse の
  add.value を pre-state から取得する契約は、id 一致 remove の StateDiffChange 自体が
  フル内容を持たない(id のみで対象を特定する)設計と整合させるために必要。
- **代替案**: 事前存在確認バリデーションフェーズを追加する(選択肢 A) — 却下(新規バリデーション
  ステップの追加コストに見合う利点がなく、apply-time reject 経路と機能的に重複する)。
  存在しない要素への remove を no-op として許容する(選択肢 C) — 却下(監査可能性の後退)。

### D123: 停止条件判定用フィールド(CharacterState.status / SceneState.status)

`CharacterState.status`(alive/dead/missing、既定 alive)と `SceneState.status`(active/ended、既定 active)を追加し、他フィールドと同じ dot-path StateDiff(`op: set, path: status`)で変更できるようにする(spec-foundation §4.4 D123。session-autonomy の `character_death`/`scene_end` 停止条件を機械的に評価可能にするため。新規の判定機構は導入せず既存の StateDiff 検証・適用パスに乗せる)。

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

> relationship の対象特定方式(D116)、`SceneState.hidden_facts` の構造化(D115)、id 一致
> `remove` の対象不在時の挙動と inverse 生成における pre-state 参照(Q3 recommendation B)は
> 解決済み。上記「Decisions」セクションの対応する項目を参照。詳細な検討経緯は
> `openspec/grill/Grill-add-state-model-20260703.md` を参照。
