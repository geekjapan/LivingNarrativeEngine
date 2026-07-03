# random-engine Specification

## Purpose
TBD - created by archiving change add-random-engine. Update Purpose after archive.
## Requirements
### Requirement: Seed に基づく決定的 RNG 初期化
Random Engine は `project.random_seed`(文字列)から決定的な RNG ストリームを初期化しなければならない(SHALL)。同一の `random_seed` から初期化した RNG は、同一順序で同一回数呼び出された場合、常に同一の乱数列を生成しなければならない(SHALL)。文字列 seed は安定したハッシュ(例: SHA-256)を経て整数シードへ変換し、Python バージョンやプロセスをまたいでも同じ変換結果になることを保証しなければならない(SHALL)。

#### Scenario: 同一 seed からの初期化は同一列を生成する
- **WHEN** 同じ `random_seed` の値で Random Engine を2回初期化し、それぞれから同数の draw を行う
- **THEN** 2回の draw 列は完全に一致する

#### Scenario: 異なる seed は異なる列を生成する
- **WHEN** 異なる `random_seed` の値で Random Engine を初期化し、同数の draw を行う
- **THEN** 2回の draw 列が一致する確率は無視できるほど低く、実装は異なる列を返す

### Requirement: Roll id の採番と RNG 状態の再構築
Random Engine が生成する全ての roll レコードは project 内で一意かつ単調増加する roll id(`roll_NNNN`)を持たなければならない(SHALL)。この roll id の採番は、RNG から実際に draw した回数(RNG 消費数)とは独立したカウンタで管理しなければならない(SHALL)。ロール種別ごとの RNG 消費数は固定されていなければならない(SHALL): ダイス roll(`NdM`)は N 回、確率判定は1回、weighted table 選択は1回、reroll は再実行する元ロールと同じ種別・同じ消費数、GM override は0回。RNG の状態は `random_seed` と「これまでに消費した draw 数」のみから一意に再構築できなければならない(SHALL)。これにより、セッションの中断・resume 後も同一の乱数列を継続できる。

#### Scenario: 消費数からの状態再構築でシーケンスが継続する
- **WHEN** ある `random_seed` の RNG で N 回 draw した後にプロセスを終了し、同じ `random_seed` と消費数 N から RNG を再初期化して1回 draw する
- **THEN** その draw の結果は、中断せず N+1 回目として連続 draw した場合の結果と一致する

#### Scenario: roll id と RNG 消費数は独立して増加する
- **WHEN** GM override を1回実行した直後に新しいダイス roll を1回実行する
- **THEN** GM override によって roll id は1つ進むが RNG 消費数は増えず、続くダイス roll の RNG 消費数は GM override 直前の状態から連続する

#### Scenario: NdM のダイス roll は N 回の draw を消費する
- **WHEN** `"3d6"` のダイス roll を1回実行する
- **THEN** RNG 消費数は3増加し、roll id は1つだけ増加する

#### Scenario: ターンで消費した draw 回数が問い合わせ可能である
- **WHEN** あるターンの実行中に Random Engine が K 回 draw する
- **THEN** そのターン開始時点からの消費数の差分として K を呼び出し側が取得でき、turn-pipeline がこれをそのターンの `meta.yaml` に記録できる

### Requirement: ダイス記法のパース
Random Engine は `NdM`、`NdM+K`、`NdM-K` 形式のダイス記法をパースしなければならない(SHALL)。N(振る個数)は 1 以上 100 以下、M(面数)は 1 以上 1000 以下でなければならない(SHALL)。この範囲を超える、または記法が不正な入力に対しては、パース処理を実行せず、原因を示す明確なエラーを返さなければならない(SHALL)。ダイス roll は省略可能な `target`(整数の閾値)を受け取ることができ、指定された場合は結果値が target 以上であれば success、そうでなければ failure として outcome を算出しなければならない(SHALL)。target を指定しない場合、outcome は算出されない。

#### Scenario: 正常なダイス記法をパースする
- **WHEN** `"2d6+3"` をパースする
- **THEN** N=2, M=6, 修正値=+3 として解釈され、結果値は 2〜6 の出目合計に 3 を加えた 5〜15 の範囲に収まる

#### Scenario: 上限を超えるダイス記法は拒否される
- **WHEN** `"101d6"` または `"2d1001"` をパースする
- **THEN** ダイスは振られず、上限超過を示すパースエラーが返される

#### Scenario: 不正な記法は拒否される
- **WHEN** `"d6"` や `"2x6"` のように形式が一致しない文字列をパースする
- **THEN** ダイスは振られず、どこが不正かを示すパースエラーが返される

#### Scenario: target 指定時に outcome が算出される
- **WHEN** `"2d6"` を target=7 でロールし、結果値が7以上になる
- **THEN** outcome は success として算出され、結果値が6以下の場合は failure となる

### Requirement: 確率判定(base_chance + modifiers)
Random Engine は base_chance(0〜100)と、名前付き符号付き modifier のリストを受け取り、それらの合計を final_chance として算出し、0〜100の範囲にクランプしなければならない(SHALL)。判定は RNG から d100(1〜100)を1回 draw し、roll 値が final_chance 以下であれば success、それ以外は failure としなければならない(SHALL)。

#### Scenario: modifier 合計が範囲内に収まる場合
- **WHEN** base_chance=55、modifiers が `weather: +10`, `fatigue: -15` である確率判定を実行する
- **THEN** final_chance は 50 として算出され、d100 roll の結果が 50 以下なら success、51 以上なら failure と判定される

#### Scenario: final_chance が範囲外になる場合はクランプされる
- **WHEN** base_chance と modifiers の合計が 100 を超える、または 0 未満になる確率判定を実行する
- **THEN** final_chance はそれぞれ 100 または 0 にクランプされてから判定に用いられる

### Requirement: Weighted event table からの選択
Random Engine は、重みを持つエントリのリストを受け取り、重みに比例した確率で1エントリを選択しなければならない(SHALL)。条件(condition)の評価は呼び出し側の責務であり、Random Engine は呼び出し側が渡した「選択対象となる eligible エントリ集合」の中からのみ選択する(SHALL)。個々のエントリの重みは0以上でなければならない(SHALL)。全エントリの重み合計が0以下、エントリ集合が空、または負の重みを持つエントリが1件でも含まれる場合は選択を実行せず、明確なエラーを返さなければならない(SHALL)。

#### Scenario: 重みに応じてエントリが選択される
- **WHEN** 重み 70 と 30 の2エントリを持つ table から1回選択する
- **THEN** 選択結果はいずれか一方のエントリであり、十分な回数試行した際の選択比率は重み比率に収束する

#### Scenario: 空の eligible エントリ集合はエラーになる
- **WHEN** eligible エントリが0件、または全エントリの重み合計が0の table から選択しようとする
- **THEN** 選択は行われず、選択不能を示すエラーが返される

#### Scenario: 負の重みを持つエントリはエラーになる
- **WHEN** 重み -10 を含むエントリ集合から選択しようとする
- **THEN** 選択は行われず、不正な重みを示すエラーが返される

### Requirement: Roll ログの永続化
発生した全ての roll(ダイス、確率判定、weighted table 選択)は、そのターンの `rolls.yaml` に追記されなければならない(SHALL)。各 roll レコードは project 全体で一意な id `roll_NNNN`(ゼロパディング、project 内通番)、発生ターン番号(turn)、種別(type: `dice` | `chance` | `table`)、入力(dice記法+任意の target、または base_chance/modifiers/final_chance、または table 名+eligible エントリ)、結果値、target 指定時または確率判定時の outcome を記録しなければならない(SHALL、企画書 §14.9 準拠)。呼び出し側は、type に依らず任意のラベル(企画書 §14.9 の `type: detection_check` のような意味的名称)と consequences(自由文リスト)を追加で渡すことができ、Random Engine はこれを解釈せずそのまま roll レコードへ保存しなければならない(SHALL)。さらに各 roll レコードは、任意フィールドとして `supersedes`(reroll / GM override 時に置き換え対象の元 roll id を参照。通常 roll では省略)と `override`(GM override であることを機械的に判別する真偽値、既定 `false`)を持たなければならない(SHALL、Requirement「Reroll の履歴保存」「GM override の履歴保存」参照。下流の reader / exporter が新旧レコード・手動上書きを区別できるようにするため)。加えて各 roll レコードは、任意フィールドとして `severity`(`normal` | `critical` の enum、既定 `normal`)を持たなければならない(SHALL、spec-foundation §4.4 D123)。`severity` は呼び出し側(Conflict Resolver)が明示的に指定した値をそのまま保存するパススルーのフィールドであり(SHALL)、Random Engine 自身がロール結果から `severity` を自動判定するロジックを実装してはならない(MUST NOT、判定基準の設計は agent-runtime capability の責務。session-autonomy の `heavy_roll_failure` 停止条件が `severity == critical` かつ失敗 `outcome` を機械的に判定するための材料)。

#### Scenario: ダイス roll が rolls.yaml に記録される
- **WHEN** あるターンでダイス判定を1回実行する
- **THEN** そのターンの `rolls.yaml` に、一意な `roll_NNNN` id、dice記法、出目、修正後の結果値を含むレコードが追記される

#### Scenario: 確率判定 roll が rolls.yaml に記録される
- **WHEN** あるターンで確率判定を1回実行する
- **THEN** そのターンの `rolls.yaml` に、base_chance・modifiers・final_chance・d100 roll値・outcome を含むレコードが追記される

#### Scenario: roll id はプロジェクト全体で一意である
- **WHEN** 複数ターンにまたがって roll を実行する
- **THEN** 全ての roll id はプロジェクト内で重複しない通番として採番される

#### Scenario: 呼び出し側のラベルと consequences が透過的に保存される
- **WHEN** 呼び出し側が `label: "stealth_check"` と `consequences: ["リナは追跡者に気づかない"]` を付与してダイス roll を実行する
- **THEN** `rolls.yaml` のレコードにはそれらの値がそのまま保存され、Random Engine はその内容を検証・解釈しない

#### Scenario: 呼び出し側が指定した severity がそのまま記録される
- **WHEN** 呼び出し側が `severity: critical` を指定してダイス roll を実行する
- **THEN** `rolls.yaml` のレコードに `severity: critical` がそのまま保存され、Random Engine はその値を自動判定・上書きしない

### Requirement: Reroll の履歴保存
Reroll は既存 roll レコードを上書きしてはならない(SHALL NOT)。Reroll は新しい `roll_NNNN` id を持つ新規レコードとして記録され、元の roll id を `supersedes` フィールドで参照しなければならない(SHALL)。Reroll は元ロールと同じ種別・同じ RNG 消費数で、現在の RNG ストリーム位置から新規に draw しなければならない(SHALL)。過去の消費数へ巻き戻して同じ乱数列を再取得することは SHALL NOT。

#### Scenario: reroll が新規レコードとして追記される
- **WHEN** `roll_0018` に対して reroll を実行する
- **THEN** 新しい roll id(例: `roll_0031`)を持つレコードが `rolls.yaml` に追記され、`supersedes: roll_0018` を含む。`roll_0018` のレコードは変更されない

### Requirement: GM override の履歴保存
GM override(GM がロール結果を手動で変更する操作)は既存 roll レコードを上書きしてはならない(SHALL NOT)。Override は新しい `roll_NNNN` id を持つ新規レコードとして記録され、`supersedes` フィールドで元の roll id を参照し、override であることを示す属性(`override: true`)を持たなければならない(SHALL)。GM override は RNG を一切消費してはならない(SHALL NOT)。roll id のみが1つ進む。

#### Scenario: GM override が新規レコードとして追記される
- **WHEN** GM が `roll_0018` の outcome を failure から success に上書きする
- **THEN** 新しい roll id を持つレコードが `rolls.yaml` に追記され、`supersedes: roll_0018` と override であることを示す情報、および上書き後の outcome を含む。`roll_0018` の元レコードは変更されない

### Requirement: 同一条件下での再現性
同一の `random_seed`、同一の呼び出し順序・呼び出し内容(ダイス記法、確率判定の入力、weighted table のエントリと eligible 集合)であれば、Random Engine は常に同一の roll 結果列を生成しなければならない(SHALL)。これは spec-foundation §7 の「同一 seed + 同一介入列 + mock provider ⇒ 完全再現」という回帰テスト基盤の前提を満たすものである。

#### Scenario: 同一入力列に対する再現性
- **WHEN** 同一の `random_seed` で初期化した Random Engine に対し、同一順序で同一のダイス記法・確率判定・weighted table 呼び出しを行う
- **THEN** 全ての roll 結果(出目、final_chance、outcome、選択エントリ)が前回実行と完全に一致する

