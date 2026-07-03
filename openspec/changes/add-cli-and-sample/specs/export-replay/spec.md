# export-replay

## ADDED Requirements

### Requirement: turn artifactからのreplay.md組み立て
export-replay は、対象プロジェクトの `workspace/runs/turn_NNNN/` に保存された turn artifact(`narration.md`・`intervention.yaml`・`rolls.yaml`・`state_diff.yaml`)を、ターン番号の昇順に読み込み、単一の `replay.md` ファイルへ組み立てなければならない(SHALL)。組み立ては `applied` 済みのターンのみを対象とし、`pending_review`/`stopped_for_review`/`failed` のターンは本文には含めず、後述のギャップ処理に従わなければならない(SHALL)。

#### Scenario: applied済み全ターンの組み立て
- **WHEN** ターン1〜10がすべて `applied` 済みのプロジェクトで export-replay を実行する
- **THEN** `replay.md` にターン1〜10の `narration.md` 本文がターン番号順に含まれる

### Requirement: novelスタイル出力
`style: novel` を指定した場合、export-replay は各ターンの `narration.md` 本文のみを連結した、システムログ的な注釈を含まない連続した散文として `replay.md` を生成しなければならない(SHALL)。

#### Scenario: novelスタイルでの出力
- **WHEN** `--style novel` を指定して export-replay を実行する
- **THEN** `replay.md` にはターン番号見出しや intervention/roll の注釈が含まれず、本文が連続した散文として出力される

### Requirement: logスタイル出力
`style: log` を指定した場合、export-replay は各ターンごとにターン見出し(ターン番号)、そのターンに適用された intervention の要約、発生した roll の要約、適用された state diff の要約を、`narration.md` 本文と併せて注釈として出力しなければならない(SHALL)。

#### Scenario: logスタイルでの注釈出力
- **WHEN** intervention と roll が発生したターンに対して `--style log` を指定して export-replay を実行する
- **THEN** 当該ターンのブロックに、ターン見出し・intervention要約・roll要約・適用diff要約・narration本文がこの順に含まれる

### Requirement: 決定性とLLM呼び出しの禁止
export-replay は、保存済みの turn artifact のみを入力として `replay.md` を組み立てなければならず(SHALL)、実行中に LLM provider を一切呼び出してはならない(MUST NOT)。同一の turn artifact 集合に対して export-replay を複数回実行した場合、生成される `replay.md` はバイト単位で同一でなければならない(SHALL)。

#### Scenario: 再実行での出力一致
- **WHEN** 同一プロジェクトに対して export-replay を2回連続で実行する
- **THEN** 2回分の `replay.md` の内容がバイト単位で完全に一致する

### Requirement: 失敗・停止ターンのギャップ処理
`pending_review`・`stopped_for_review`・`failed` のターンが存在する場合、export-replay はそのターンの本文を出力せず、`replay.md` 内の該当箇所にギャップが存在する旨(ターン番号とステータス)を明示するプレースホルダを挿入しなければならない(SHALL)。ギャップの前後にある `applied` 済みターンの内容は欠落させてはならない(MUST NOT)。

#### Scenario: 未解決ターンを含む場合のギャップ表記
- **WHEN** ターン4が `stopped_for_review` のまま残っているプロジェクトで export-replay を実行する
- **THEN** `replay.md` のターン3とターン5の間に、ターン4が未解決(`stopped_for_review`)である旨のプレースホルダが挿入され、ターン3・5の本文は完全に出力される

### Requirement: reader可視性の遵守
export-replay が読み込む情報は、spec-foundation §4 の Reader State に相当する情報(`narration.md` 本文、および reader 可視な intervention/roll/diff の要約)に限られなければならず(SHALL)、`gm_vault` の内容、`hidden_facts`、キャラクターの `secrets`・`private_mind` を `replay.md` に一切含めてはならない(MUST NOT)。

#### Scenario: 隠し真実が出力に含まれない
- **WHEN** `gm_vault` に隠し真実が存在するプロジェクトで、いずれのターンもその真実を reader へ開示していない状態(`reveal_control` による開示無し)で export-replay を実行する
- **THEN** `replay.md` の全文に、当該隠し真実の文言が一切含まれない

### Requirement: 出力ファイルの書き込みとエラー処理
export-replay は `--output <file>` で指定したパスへ `replay.md` を書き込まなければならない(SHALL)。出力先の親ディレクトリが存在しない場合は作成しなければならない(SHALL)。対象プロジェクトに `applied` 済みターンが1件も存在しない場合、export-replay は空の `replay.md` を生成せず、明示的なエラーで終了しなければならない(SHALL)。

#### Scenario: 出力先ディレクトリの自動作成
- **WHEN** 存在しない `out/` ディレクトリ配下の `out/replay.md` を `--output` に指定して export-replay を実行する
- **THEN** `out/` ディレクトリが作成され、その配下に `replay.md` が生成される

#### Scenario: appliedターンが無い場合のエラー
- **WHEN** `init` 直後で1ターンも実行していないプロジェクトに対して export-replay を実行する
- **THEN** export-replay は `replay.md` を生成せず、対象ターンが無い旨のエラーで終了する
