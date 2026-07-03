# narration

## ADDED Requirements

### Requirement: reader可視情報のみからの入力構築
Narrator への入力は spec-foundation §4.3 の不変条件2に従い、Reader State・現シーンの reader_visible_facts・そのターンの reader 可視イベントのみから構築されなければならない(SHALL)。GM Vault・hidden_facts・他キャラクターの secrets や private_mind を Narrator の入力に含めてはならない(MUST NOT)。

#### Scenario: hidden_factsが入力に含まれない
- **WHEN** シーンに `hidden_facts` が存在し、そのターンのイベントに `visibility: gm_only` のイベントが含まれる状態で Narrate フェーズを実行する
- **THEN** Narrator に渡されるコンテキストに当該 `hidden_facts` および `gm_only` イベントの内容が一切含まれない

### Requirement: 日本語散文生成
Narrator は `project.language` に従って物語散文を生成しなければならない(SHALL)。本 change の対象プロジェクトでは `project.language` が日本語(`ja`)の場合、出力は日本語散文でなければならない。テストにおける機械的な最小判定基準は「`narration.md` の本文が空でなく、ひらがな・カタカナ・CJK 統合漢字のいずれかの文字を1文字以上含む」こととする(SHALL、openspec/config.yaml の testability ルールに対応する判定基準。散文としての品質・自然さの評価は機械判定の対象外とし、GM review gate に委ねる)。

#### Scenario: 日本語プロジェクトでの出力
- **WHEN** `project.language` が `ja` のプロジェクトで Narrate フェーズを実行する
- **THEN** `narration.md` に書き出される本文は空でなく、ひらがな・カタカナ・CJK 統合漢字のいずれかの文字を1文字以上含む(日本語散文の機械的最小判定基準)

### Requirement: renderer レジストリと出力形式選択
Narrator は D108 のレジストリ方式で登録された renderer を介して出力形式を選択しなければならない(SHALL)。本 change では `novel`(既定)と `log`(ターン/イベント箇条書き形式)の2種類の renderer を提供する。renderer は `project.renderer` によって選択され、呼び出し単位で上書き可能でなければならない。

#### Scenario: project.rendererがnovelの場合の既定出力
- **WHEN** `project.renderer` が未設定または `novel` のプロジェクトで Narrate フェーズを実行する
- **THEN** `narration.md` は小説風の連続した散文として整形される

#### Scenario: logスタイルでの呼び出し単位の上書き
- **WHEN** `project.renderer` が `novel` のプロジェクトで、Narrate フェーズ呼び出し時に明示的に `log` スタイルを指定する
- **THEN** `narration.md` はターン/イベント単位の箇条書きログ形式として整形され、プロジェクト既定の `novel` は使用されない

### Requirement: 長さ・トーンのガイダンス入力
Narrator はシーンの `mood` と、intervention の `tone_control` 制約(値)を長さ・トーンの guidance として受け取れなければならない(SHALL)。本 change では intervention の完全な解釈・生成は対象外であり、Narrator は渡された制約値をそのまま guidance として利用する(生成しない場合は既定 guidance を用いる)。

#### Scenario: tone_control制約が渡された場合
- **WHEN** シーンの `mood` と intervention の `tone_control` 制約値を指定して Narrate フェーズを実行する
- **THEN** Narrator への呼び出し引数に渡した `mood` と `tone_control` 値がそのまま含まれる

#### Scenario: tone_control制約が無い場合の既定挙動
- **WHEN** intervention が空(この change の Intervene フェーズの既定挙動)の状態で Narrate フェーズを実行する
- **THEN** Narrator はシーンの `mood` のみを guidance として使用し、例外を発生させずに `narration.md` を生成する

### Requirement: narration.md artifact のフロントマター
`narration.md` は本文の前にフロントマターを持ち、少なくとも `turn`(ターン番号)・`style`(使用した renderer 名)・`visibility: reader` を含まなければならない(SHALL)。

#### Scenario: フロントマターの検証
- **WHEN** `turn_0003` で `log` スタイルの Narrate フェーズを完了させる
- **THEN** `workspace/runs/turn_0003/narration.md` のフロントマターに `turn: 3` `style: log` `visibility: reader` が含まれる

### Requirement: 未実装renderer指定時のエラー
`project.renderer` またはフェーズ呼び出し時の style 上書きが未登録の renderer 名を指定した場合、TurnPipeline は既定 renderer にフォールバックせず、明示的なエラーを送出しなければならない(SHALL)。

#### Scenario: 未登録styleの指定
- **WHEN** レジストリに存在しない renderer 名(例: `script`)を Narrate フェーズの style として指定する
- **THEN** Narrate フェーズは例外を送出し、Check/Commit フェーズへ進まずにターンステータスが `failed` になる
