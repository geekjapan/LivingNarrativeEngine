# export-replay

## ADDED Requirements

### Requirement: turn artifactからのreplay.md組み立て
export-replay は、対象プロジェクトの `workspace/runs/turn_NNNN/` に保存された turn artifact(`meta.yaml`・`narration.md`・`intervention.yaml`・`rolls.yaml`・`events.yaml`・`state_diff.yaml`、および存在する場合は `review.yaml`)を、ターン番号の昇順に読み込み、単一の `replay.md` ファイルへ組み立てなければならない(SHALL)。`review.yaml` はレビューゲートを経たターンにのみ存在する任意 artifact であり(commit-mode `auto` 等で自動適用されたターンには存在しない)、欠落をエラーとして扱ってはならず(MUST NOT)、`decision` の検査はファイルが存在する場合にのみ行わなければならない(SHALL)。各ターンのステータス(`applied`/`pending_review`/`stopped_for_review`/`failed`)は `meta.yaml` の `status` フィールド(turn-pipeline、spec-foundation §9 D111)を正本として判定しなければならない(SHALL)。組み立ては `status: applied` のターンのうち、`review.yaml` が存在しかつその `decision` が `reject_all` であるもの(spec-foundation §9 D120)を除いたターンのみを本文対象とし(`review.yaml` の無い `applied` ターンは常に本文対象)、`pending_review`/`stopped_for_review`/`failed` のターン、および `decision: reject_all` の `applied` ターンは本文には含めず、後述のギャップ処理に従わなければならない(SHALL)。

#### Scenario: review.yaml の無い自動適用ターンは本文対象になる
- **WHEN** commit-mode `auto` で適用され `review.yaml` を持たないターンを含むプロジェクトに対して export-replay を実行する
- **THEN** export はエラーにならず、当該ターンの narration は本文として `replay.md` に含まれる

#### Scenario: applied済み全ターンの組み立て
- **WHEN** ターン1〜10のすべてで `meta.yaml` の `status` が `applied` であり、`reject_all` の決定を持つターンが無いプロジェクトで export-replay を実行する
- **THEN** `replay.md` にターン1〜10の `narration.md` 本文がターン番号順に含まれる

### Requirement: novelスタイル出力
`style: novel` を指定した場合、export-replay は各ターンの `narration.md` 本文のみを連結した、システムログ的な注釈を含まない連続した散文として `replay.md` を生成しなければならない(SHALL)。

#### Scenario: novelスタイルでの出力
- **WHEN** `--style novel` を指定して export-replay を実行する
- **THEN** `replay.md` にはターン番号見出しや intervention/roll の注釈が含まれず、本文が連続した散文として出力される

### Requirement: logスタイル出力
`style: log` を指定した場合、export-replay は各ターンごとにターン見出し(ターン番号)、そのターンに適用された intervention の要約、reader 可視な roll の要約(Requirement「reader可視性の遵守」の導出規則に従い、当該ターンの reader 可視イベントが持つ `Event.roll_ids` が参照する roll のみを対象とする、spec-foundation §9 D121)、適用された state diff の要約を、`narration.md` 本文と併せて注釈として出力しなければならない(SHALL)。

#### Scenario: logスタイルでの注釈出力
- **WHEN** intervention と roll が発生したターンに対して `--style log` を指定して export-replay を実行する
- **THEN** 当該ターンのブロックに、ターン見出し・intervention要約・roll要約・適用diff要約・narration本文がこの順に含まれる

### Requirement: 決定性とLLM呼び出しの禁止
export-replay は、保存済みの turn artifact のみを入力として `replay.md` を組み立てなければならず(SHALL)、実行中に LLM provider を一切呼び出してはならない(MUST NOT)。同一の turn artifact 集合に対して export-replay を複数回実行した場合、生成される `replay.md` はバイト単位で同一でなければならない(SHALL)。

#### Scenario: 再実行での出力一致
- **WHEN** 同一プロジェクトに対して export-replay を2回連続で実行する
- **THEN** 2回分の `replay.md` の内容がバイト単位で完全に一致する

### Requirement: 失敗・停止・却下ターンのギャップ処理
`meta.yaml` の `status` フィールド(spec-foundation §9 D111)が `pending_review`・`stopped_for_review`・`failed` のターン、および `status: applied` だが `review.yaml` の `decision` が `reject_all`(spec-foundation §9 D120、state への実変更がゼロのまま解決されたターン)であるターンは、いずれもギャップとして扱い、そのターンの本文を出力してはならない(MUST NOT)。ギャップの表現はスタイルごとに次のとおりでなければならない(SHALL): `style: log` では該当箇所にギャップが存在する旨(ターン番号とステータス、`reject_all` の場合はその旨)を明示するプレースホルダを挿入する。`style: novel` では当該ターンを一切の注釈・プレースホルダなく省略する(SHALL NOT プレースホルダを挿入してはならない — novelスタイル出力の「システムログ的な注釈を含まない」契約と整合させる)。ギャップの前後にある本文対象ターンの内容は欠落させてはならない(MUST NOT)。

#### Scenario: 未解決ターンを含む場合のギャップ表記(logスタイル)
- **WHEN** ターン4が `stopped_for_review` のまま残っているプロジェクトで `--style log` を指定して export-replay を実行する
- **THEN** `replay.md` のターン3とターン5の間に、ターン4が未解決(`stopped_for_review`)である旨のプレースホルダが挿入され、ターン3・5の本文は完全に出力される

#### Scenario: 未解決ターンの省略(novelスタイル)
- **WHEN** ターン4が `stopped_for_review` のまま残っているプロジェクトで `--style novel` を指定して export-replay を実行する
- **THEN** `replay.md` にはターン4に関する本文・注釈のいずれも含まれず、ターン3とターン5の本文がそのまま連続する

#### Scenario: reject_allターンの省略(novelスタイル)
- **WHEN** ターン4の `review.yaml` の `decision` が `reject_all` であるプロジェクトで `--style novel` を指定して export-replay を実行する
- **THEN** `replay.md` にはターン4に関する本文・注釈のいずれも含まれず、ターン3とターン5の本文がそのまま連続する

#### Scenario: reject_allターンのギャップ表記(logスタイル)
- **WHEN** ターン4の `review.yaml` の `decision` が `reject_all` であるプロジェクトで `--style log` を指定して export-replay を実行する
- **THEN** `replay.md` のターン4に対応する箇所に、当該ターンが `reject_all` によって状態へ反映されなかった旨のプレースホルダが挿入される

### Requirement: reader可視性の遵守
export-replay が読み込む情報は、spec-foundation §4 の Reader State に相当する情報(`narration.md` 本文、および reader 可視な intervention/roll/diff の要約)に限られなければならず(SHALL)、`gm_vault` の内容、`hidden_facts`、キャラクターの `secrets`・`private_mind` を `replay.md` に一切含めてはならない(MUST NOT)。roll レコード自体は `visibility` フィールドを持たない(add-random-engine、spec-foundation §9 D121)ため、export-replay は roll 自身の可視性を直接判定してはならず(SHALL NOT)、当該ターンの `events.yaml` に含まれる reader 可視イベント(spec-foundation §4 の可視性判定に従う)の `Event.roll_ids` が参照する roll のみを reader 可視な roll として扱い、いずれの reader 可視イベントの `roll_ids` からも参照されない roll は `replay.md` に一切含めてはならない(MUST NOT)。

#### Scenario: 隠し真実が出力に含まれない
- **WHEN** `gm_vault` に隠し真実が存在するプロジェクトで、いずれのターンもその真実を reader へ開示していない状態(`reveal_control` による開示無し)で export-replay を実行する
- **THEN** `replay.md` の全文に、当該隠し真実の文言が一切含まれない

#### Scenario: reader不可視イベントにのみ紐づくrollの除外
- **WHEN** あるターンの roll が `gm_only` イベントの `roll_ids` からのみ参照され、いずれの reader 可視イベントの `roll_ids` からも参照されない
- **THEN** `--style log` で export-replay を実行しても、`replay.md` の当該ターンの roll 要約にその roll は一切含まれない

### Requirement: 出力ファイルの書き込みとエラー処理
export-replay は `--output <file>` で指定したパスへ `replay.md` を書き込まなければならない(SHALL)。出力先の親ディレクトリが存在しない場合は作成しなければならない(SHALL)。本文対象ターン(`status: applied` かつ、`review.yaml` が存在しないかその `decision` が `reject_all` でないターン。Requirement「失敗・停止・却下ターンのギャップ処理」のフィルタリング後に残るターン)が1件も存在しない場合、export-replay は空の `replay.md` を生成せず、明示的なエラーで終了しなければならない(SHALL、`applied` ターンが存在してもその全てが `reject_all` であれば同様にエラーとする)。

#### Scenario: 出力先ディレクトリの自動作成
- **WHEN** 存在しない `out/` ディレクトリ配下の `out/replay.md` を `--output` に指定して export-replay を実行する
- **THEN** `out/` ディレクトリが作成され、その配下に `replay.md` が生成される

#### Scenario: appliedターンが無い場合のエラー
- **WHEN** `init` 直後で1ターンも実行していないプロジェクトに対して export-replay を実行する
- **THEN** export-replay は `replay.md` を生成せず、対象ターンが無い旨のエラーで終了する
