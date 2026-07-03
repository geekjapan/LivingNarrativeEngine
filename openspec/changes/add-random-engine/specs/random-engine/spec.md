## ADDED Requirements

### Requirement: Seed に基づく決定的 RNG 初期化
Random Engine は `project.random_seed`(文字列)から決定的な RNG ストリームを初期化しなければならない(SHALL)。同一の `random_seed` から初期化した RNG は、同一順序で同一回数呼び出された場合、常に同一の乱数列を生成しなければならない(SHALL)。文字列 seed は安定したハッシュ(例: SHA-256)を経て整数シードへ変換し、Python バージョンやプロセスをまたいでも同じ変換結果になることを保証しなければならない(SHALL)。

#### Scenario: 同一 seed からの初期化は同一列を生成する
- **WHEN** 同じ `random_seed` の値で Random Engine を2回初期化し、それぞれから同数の draw を行う
- **THEN** 2回の draw 列は完全に一致する

#### Scenario: 異なる seed は異なる列を生成する
- **WHEN** 異なる `random_seed` の値で Random Engine を初期化し、同数の draw を行う
- **THEN** 2回の draw 列が一致する確率は無視できるほど低く、実装は異なる列を返す

### Requirement: Roll の通番管理と RNG 状態の再構築
Random Engine が消費する全ての乱数draw(ダイス、確率判定、weighted table 選択)は、project 内で一意な通番(sequence)を持たなければならない(SHALL)。RNG の状態は `random_seed` と「これまでに消費した draw 数」のみから一意に再構築できなければならない(SHALL)。これにより、セッションの中断・resume 後も同一の乱数列を継続できる。

#### Scenario: 消費数からの状態再構築でシーケンスが継続する
- **WHEN** ある `random_seed` の RNG で N 回 draw した後にプロセスを終了し、同じ `random_seed` と消費数 N から RNG を再初期化して1回 draw する
- **THEN** その draw の結果は、中断せず N+1 回目として連続 draw した場合の結果と一致する

#### Scenario: turn meta に消費数が記録される
- **WHEN** あるターンの実行中に Random Engine が K 回 draw する
- **THEN** そのターンの `meta.yaml` に rng 消費数として K が記録される

### Requirement: ダイス記法のパース
Random Engine は `NdM`、`NdM+K`、`NdM-K` 形式のダイス記法をパースしなければならない(SHALL)。N(振る個数)は 1 以上 100 以下、M(面数)は 1 以上 1000 以下でなければならない(SHALL)。この範囲を超える、または記法が不正な入力に対しては、パース処理を実行せず、原因を示す明確なエラーを返さなければならない(SHALL)。

#### Scenario: 正常なダイス記法をパースする
- **WHEN** `"2d6+3"` をパースする
- **THEN** N=2, M=6, 修正値=+3 として解釈され、結果値は 2〜6 の出目合計に 3 を加えた 5〜15 の範囲に収まる

#### Scenario: 上限を超えるダイス記法は拒否される
- **WHEN** `"101d6"` または `"2d1001"` をパースする
- **THEN** ダイスは振られず、上限超過を示すパースエラーが返される

#### Scenario: 不正な記法は拒否される
- **WHEN** `"d6"` や `"2x6"` のように形式が一致しない文字列をパースする
- **THEN** ダイスは振られず、どこが不正かを示すパースエラーが返される

### Requirement: 確率判定(base_chance + modifiers)
Random Engine は base_chance(0〜100)と、名前付き符号付き modifier のリストを受け取り、それらの合計を final_chance として算出し、0〜100の範囲にクランプしなければならない(SHALL)。判定は RNG から d100(1〜100)を1回 draw し、roll 値が final_chance 以下であれば success、それ以外は failure としなければならない(SHALL)。

#### Scenario: modifier 合計が範囲内に収まる場合
- **WHEN** base_chance=55、modifiers が `weather: +10`, `fatigue: -15` である確率判定を実行する
- **THEN** final_chance は 50 として算出され、d100 roll の結果が 50 以下なら success、51 以上なら failure と判定される

#### Scenario: final_chance が範囲外になる場合はクランプされる
- **WHEN** base_chance と modifiers の合計が 100 を超える、または 0 未満になる確率判定を実行する
- **THEN** final_chance はそれぞれ 100 または 0 にクランプされてから判定に用いられる

### Requirement: Weighted event table からの選択
Random Engine は、重みを持つエントリのリストを受け取り、重みに比例した確率で1エントリを選択しなければならない(SHALL)。条件(condition)の評価は呼び出し側の責務であり、Random Engine は呼び出し側が渡した「選択対象となる eligible エントリ集合」の中からのみ選択する(SHALL)。全エントリの重み合計が0以下、またはエントリ集合が空の場合は選択を実行せず、明確なエラーを返さなければならない(SHALL)。

#### Scenario: 重みに応じてエントリが選択される
- **WHEN** 重み 70 と 30 の2エントリを持つ table から1回選択する
- **THEN** 選択結果はいずれか一方のエントリであり、十分な回数試行した際の選択比率は重み比率に収束する

#### Scenario: 空の eligible エントリ集合はエラーになる
- **WHEN** eligible エントリが0件、または全エントリの重み合計が0の table から選択しようとする
- **THEN** 選択は行われず、選択不能を示すエラーが返される

### Requirement: Roll ログの永続化
発生した全ての roll(ダイス、確率判定、weighted table 選択)は、そのターンの `rolls.yaml` に追記されなければならない(SHALL)。各 roll レコードは project 全体で一意な id `roll_NNNN`(ゼロパディング、project 内通番)を持ち、種別(type)、入力(dice記法 または base_chance/modifiers/final_chance)、結果値、outcome、consequences を記録しなければならない(SHALL、企画書 §14.9 準拠)。

#### Scenario: ダイス roll が rolls.yaml に記録される
- **WHEN** あるターンでダイス判定を1回実行する
- **THEN** そのターンの `rolls.yaml` に、一意な `roll_NNNN` id、dice記法、出目、修正後の結果値を含むレコードが追記される

#### Scenario: 確率判定 roll が rolls.yaml に記録される
- **WHEN** あるターンで確率判定を1回実行する
- **THEN** そのターンの `rolls.yaml` に、base_chance・modifiers・final_chance・d100 roll値・outcome を含むレコードが追記される

#### Scenario: roll id はプロジェクト全体で一意である
- **WHEN** 複数ターンにまたがって roll を実行する
- **THEN** 全ての roll id はプロジェクト内で重複しない通番として採番される

### Requirement: Reroll の履歴保存
Reroll は既存 roll レコードを上書きしてはならない(SHALL NOT)。Reroll は新しい `roll_NNNN` id を持つ新規レコードとして記録され、元の roll id を `supersedes` フィールドで参照しなければならない(SHALL)。

#### Scenario: reroll が新規レコードとして追記される
- **WHEN** `roll_0018` に対して reroll を実行する
- **THEN** 新しい roll id(例: `roll_0031`)を持つレコードが `rolls.yaml` に追記され、`supersedes: roll_0018` を含む。`roll_0018` のレコードは変更されない

### Requirement: GM override の履歴保存
GM override(GM がロール結果を手動で変更する操作)は既存 roll レコードを上書きしてはならない(SHALL NOT)。Override は新しい `roll_NNNN` id を持つ新規レコードとして記録され、`supersedes` フィールドで元の roll id を参照し、override であることを示す属性を持たなければならない(SHALL)。

#### Scenario: GM override が新規レコードとして追記される
- **WHEN** GM が `roll_0018` の outcome を failure から success に上書きする
- **THEN** 新しい roll id を持つレコードが `rolls.yaml` に追記され、`supersedes: roll_0018` と override であることを示す情報、および上書き後の outcome を含む。`roll_0018` の元レコードは変更されない

### Requirement: 同一条件下での再現性
同一の `random_seed`、同一の呼び出し順序・呼び出し内容(ダイス記法、確率判定の入力、weighted table のエントリと eligible 集合)であれば、Random Engine は常に同一の roll 結果列を生成しなければならない(SHALL)。これは spec-foundation §7 の「同一 seed + 同一介入列 + mock provider ⇒ 完全再現」という回帰テスト基盤の前提を満たすものである。

#### Scenario: 同一入力列に対する再現性
- **WHEN** 同一の `random_seed` で初期化した Random Engine に対し、同一順序で同一のダイス記法・確率判定・weighted table 呼び出しを行う
- **THEN** 全ての roll 結果(出目、final_chance、outcome、選択エントリ)が前回実行と完全に一致する
