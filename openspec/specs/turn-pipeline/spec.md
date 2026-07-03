# turn-pipeline Specification

## Purpose
TBD - created by archiving change add-turn-pipeline. Update Purpose after archive.
## Requirements
### Requirement: フェーズ実行順序
TurnPipeline は spec-foundation §6 に定義された 8 フェーズ(Load / Intervene / Simulate / Act / Resolve / Narrate / Check / Commit)を、この順序で1ターンにつき1回ずつ実行しなければならない(SHALL)。前のフェーズが正常終了しない限り、次のフェーズを開始してはならない。

#### Scenario: mock provider による正常な8フェーズ実行
- **WHEN** mock provider・random-engine・組み込み最小スロットのみが設定されたプロジェクトで1ターンを実行する
- **THEN** Load → Intervene → Simulate → Act → Resolve → Narrate → Check → Commit の順に全フェーズが実行され、ターンステータスが `applied` または `pending_review` になる

### Requirement: Load フェーズによる TurnContext 構築
Load フェーズは project.yaml と workspace 内の全 state ファイルを読み込み、後続フェーズが参照するメモリ上の `TurnContext` を構築しなければならない(SHALL)。project または state ファイルの読み込みが検証エラーで失敗した場合、Load フェーズは `turn_NNNN` ディレクトリを作成せず、Intervene 以降のいかなるフェーズも実行してはならない(SHALL NOT)。

#### Scenario: project と state の正常なロード
- **WHEN** 妥当な `project.yaml` と全 state ファイルが揃った workspace でターンを開始する
- **THEN** Load フェーズは例外を発生させずに完了し、後続フェーズが参照できる `TurnContext` がメモリ上に構築される

#### Scenario: state ファイルの検証エラーによる中断
- **WHEN** workspace 内のいずれかの state ファイルがスキーマ検証エラーを持つ状態でターンを開始する
- **THEN** Load フェーズは検証エラーで失敗し、`turn_NNNN` ディレクトリは作成されず、Intervene 以降のフェーズは実行されない

### Requirement: Intervene フェーズの既定(無介入)動作
本 change の Intervene フェーズはユーザー入力の構造化解釈を実装しない(自由文/構造化 Interpreter は `add-intervention` が追加する)。この change の範囲では、Intervene フェーズは常に無介入として扱い、`intervention.yaml` に `turn`(ターン番号)と空リストの `interventions` のみを含む最小形式を書き出さなければならない(SHALL)。この最小形式は、後続の `add-intervention` change が「無介入時の空の intervention.yaml」の既定動作として参照・後方互換を維持すべき契約として扱う。

#### Scenario: 無介入時の intervention.yaml
- **WHEN** ユーザー入力なしでターンを実行する
- **THEN** `intervention.yaml` は `turn: <ターン番号>` と空リストの `interventions: []` を含み、それ以外のフィールドを持たない

### Requirement: スロット Protocol による差し替え可能性
Simulate / Act / Resolve / BuildDiff / Check の各フェーズは、Protocol で定義された入出力インターフェースを持つスロットとして実装されなければならない(SHALL)。TurnPipeline はスロットの具体的な実装を知らず、レジストリ経由で注入されたスロットのみを呼び出さなければならない(D108/D113: レジストリ辞書、plugin loader は本 change では作らない)。BuildDiff スロットの入力は resolved events・そのターンの intervention 群(`intervention.yaml` に確定した Intervention のリスト。無介入時は空リスト)・全状態でなければならず、出力は state diff 候補と、拒否された変更候補とその理由を保持する `rejected_changes` リスト(agent-runtime の State Manager 実装が使用する。組み込み最小実装では常に空リスト)でなければならない(SHALL)。BuildDiff の契約には reveal_control の must-not-reveal 制約の遵守(読者可視スコープへの昇格を阻止すること)を含まなければならない(SHALL)。TurnPipeline は BuildDiff スロットを Narrate フェーズ完了後・Check フェーズ開始前に呼び出さなければならず(SHALL)、Check フェーズの入力には BuildDiff の出力(state diff 候補)を含めなければならない(SHALL、consistency-checks の checker は diff 候補を検査対象とするため。BuildDiff を Check の後に実行してはならない(MUST NOT))。

#### Scenario: 組み込みスロットの差し替え
- **WHEN** 後続の change が Simulate スロットを組み込み no-op 実装から別の実装に差し替えてレジストリに登録する
- **THEN** TurnPipeline のフェーズ実行順序・呼び出しコードを変更せずに新しい Simulate 実装がそのフェーズで呼び出される

### Requirement: 組み込み最小スロット実装
本 change は次の組み込みスロット実装を提供し、mock provider のみでターンが最初から最後まで実行できるようにしなければならない(SHALL): Simulate は世界イベント候補を生成しない no-op、Act は llm-provider 経由で単一キャラクターの行動候補を1件生成する trivial 実装、Resolve は行動候補・イベント候補を乱数判定を経ずにそのまま events.yaml へ渡す pass-through、BuildDiff は resolved events・そのターンの intervention 群(リスト)・全状態から state diff 候補を生成する最小実装(旧来 Commit 内部で行う想定だった diff 生成ロジックをここへ移したもの。D113)、Check は checker エラーを一切検出しない no-op。

#### Scenario: 組み込みスロットのみでのend-to-end実行
- **WHEN** キャラクターが1体・シーンが1つのプロジェクトで組み込みスロットのみを使い1ターンを実行する
- **THEN** 例外を発生させずにターンが完了し、`events.yaml` に Act スロットが生成した行動由来のイベントが1件以上含まれる

### Requirement: turn artifact ディレクトリの書き込み
TurnPipeline は各ターンにつき `workspace/runs/turn_NNNN/` ディレクトリを作成し、spec-foundation §6 の表に列挙された artifact(`intervention.yaml` `agent_io/` `events.yaml` `rolls.yaml` `narration.md` `checks.yaml` `state_diff.yaml` `meta.yaml`)を書き出さなければならない(SHALL)。`turn_NNNN` の番号は spec-foundation §3 のゼロ埋め規約に従う。

#### Scenario: 全artifactの生成
- **WHEN** ターン `turn_0001` を正常に完了させる
- **THEN** `workspace/runs/turn_0001/` 配下に `intervention.yaml` `agent_io/` `events.yaml` `rolls.yaml` `narration.md` `checks.yaml` `state_diff.yaml` `meta.yaml` がすべて存在する

### Requirement: artifact 書き込みの原子性と meta.yaml による完了マーカー
TurnPipeline は各 artifact ファイルを一時ファイルへ書き込んだ後にリネームすることで原子的に書き込まなければならない(SHALL、state-model の `StateStore.save()` と同じ tmp+rename パターン)。`meta.yaml` はそのターンの全 artifact 書き込みが完了した最後に書き込まなければならない(SHALL)。`turn_NNNN` ディレクトリが存在するが有効な `meta.yaml` を読み込めない場合(プロセスの異常終了等で書き込みが完了しなかった場合)、TurnPipeline はそのターンを未解決として扱い、後続ターンの実行をブロックしなければならない(SHALL、「次ターン番号の決定と未解決ターンによるブロック」と同じ扱い)。

#### Scenario: meta.yaml欠落ターンによるブロック
- **WHEN** `turn_0005` ディレクトリが存在するが `meta.yaml` が存在しない、または YAML として解析できない
- **THEN** TurnPipeline は新しいターンを開始せず、`turn_0005` が未解決である旨のエラーを返す

### Requirement: 失敗時の部分artifact永続化
いずれかのフェーズで例外が発生した場合、TurnPipeline はそれまでに生成済みの artifact を破棄せずにディスクへ保存しなければならない(SHALL)。例外を握り潰し、ターンが正常完了したかのように見せてはならない(MUST NOT)。

#### Scenario: Narrateフェーズでの例外
- **WHEN** Narrate フェーズで未捕捉の例外が発生する
- **THEN** それ以前のフェーズ(Load〜Resolve)が生成した artifact(`intervention.yaml` `events.yaml` `rolls.yaml` 等)がディスクに保存され、ターンステータスが `failed` になり、人間可読のエラーレポートが artifact に含まれる

### Requirement: meta.yaml の内容
`meta.yaml` は次の情報を含まなければならない(SHALL): `status`(ターンステータス。turn status の永続化先はこの meta.yaml の `status` フィールドである。D111)、フェーズごとの所要時間、LLM 呼び出し回数、`llm_tokens_total`(取得可能な範囲での全呼び出し合計トークン数。プロバイダーから取得できない場合はこのフィールド自体を省略する。1ターン内で複数の LLM プロファイルが使われた場合も全呼び出しの合算値とする。D122)、呼び出しごとの記録のリスト(各エントリは binding key・プロファイル名・model 名を持つ。D122: 1ターン内で複数 provider/model インスタンスが同時に利用されうるため、単一の「使用モデル名」ではなく呼び出しごとに記録する)、prompt hash の一覧、`rng_draws_consumed`(そのターンで消費した乱数 draw 数)、pipeline のバージョン。

#### Scenario: meta.yamlの検証
- **WHEN** 正常完了したターンの `meta.yaml` を読み込む
- **THEN** `status`・8フェーズ分の所要時間・LLM呼び出し回数(0以上の整数)・呼び出しごとの記録(binding key・プロファイル名・model 名)のリスト・prompt hash 一覧・`rng_draws_consumed`・pipeline_version フィールドがすべて存在する(`llm_tokens_total` はプロバイダーから取得できた場合のみ存在する)

#### Scenario: 複数プロファイル使用時に呼び出しごとの記録が個別に残る
- **WHEN** あるターン内で異なる binding key を通じて解決された2つの異なるプロファイルでそれぞれ LLM 呼び出しが行われる
- **THEN** `meta.yaml` の呼び出しごとの記録には、両方の呼び出しについてそれぞれの binding key・プロファイル名・model 名を含むエントリが個別に存在する

### Requirement: ターンステータスモデル
TurnPipeline は各ターンの実行結果を `applied` / `pending_review` / `stopped_for_review` / `failed` のいずれか1つのステータスとして、そのターンの `meta.yaml` の `status` フィールドへ記録しなければならない(SHALL、D111: turn status の永続化先は meta.yaml)。ステータスは全ターン artifact をスキャンすることなく、そのターンの artifact のみから判別可能でなければならない。

#### Scenario: commit-modeがauto設定でのステータス
- **WHEN** ターン実行時に commit-mode パラメータが `auto` として渡され、Check フェーズがエラーを検出せずにターンを完了する
- **THEN** ターンステータスは `applied` になり、state diff が state-model の StateStore へ適用済みである

#### Scenario: commit-modeがreview設定でのステータス
- **WHEN** ターン実行時に commit-mode パラメータが `review` として渡され、Check フェーズがエラーを検出せずにターンを完了する
- **THEN** ターンステータスは `pending_review` になり、state diff は生成されているが state-model へは未適用である

### Requirement: 次ターン番号の決定と未解決ターンによるブロック
次に実行するターン番号は「最後に `applied` されたターン番号 + 1」として決定されなければならない(SHALL)。直前のターンが `pending_review` または `stopped_for_review` の場合、それが解決される(applied または failed として確定する)まで次のターンの実行を開始してはならない(MUST NOT)。`failed` ターンを再実行する場合、TurnPipeline は同じターン番号の新規実行を開始する前に、既存の `turn_NNNN` artifact ディレクトリを `turn_NNNN_discarded_<n>`(`<n>` はそのターン番号内で既存の discarded ディレクトリと衝突しない連番)へ退避し、新規ディレクトリへ改めて全 artifact を書き込まなければならない(SHALL、上書き禁止・監査可能性維持。D112)。各 attempt の `meta.yaml` の `rng_draws_consumed` は、その attempt 単体が消費した draw 数のみを記録しなければならず(SHALL)、退避された旧試行分の消費数を合算して含めてはならない(MUST NOT)。ターン番号単位・プロジェクト全体の累積消費数(D112「RNG 累積は退避分も合算」)は、現存する `turn_NNNN/meta.yaml` と全ての `turn_NNNN_discarded_*/meta.yaml` の値を合算して算出するものとし(session-autonomy の resume / rerun 規則と同一)、同一の消費が二重に計上されてはならない(MUST NOT)。

#### Scenario: pending_reviewなターンが存在する場合のブロック
- **WHEN** `turn_0005` のステータスが `pending_review` である状態で新しいターンの実行を要求する
- **THEN** TurnPipeline は新しいターンを開始せず、`turn_0005` が未解決である旨のエラーを返す

#### Scenario: appliedなターンの後の次ターン番号
- **WHEN** `turn_0005` までのステータスがすべて `applied` である
- **THEN** 次に実行されるターンは `turn_0006` として作成される

#### Scenario: failedなターンは同じ番号で再実行される
- **WHEN** `turn_0005` が `failed` ステータスで確定した状態で次のターン実行を要求する
- **THEN** `turn_0005` は `applied` ではないため「最後に applied されたターン + 1」の計算に含まれず、次の実行は再び `turn_0005` として行われる。実行開始前に既存の `turn_0005` ディレクトリは `turn_0005_discarded_1`(既存の discarded ディレクトリがあればそれ以降の連番)へ退避され、新規の `turn_0005` ディレクトリへ新しい実行の全 artifact が書き込まれる。新しい `turn_0005/meta.yaml` の `rng_draws_consumed` は新規 attempt 単体の消費数のみを記録し、退避された `turn_0005_discarded_1` 分の消費数を含めない。プロジェクト全体の累積消費数を求める場合は、呼び出し側が現存する `turn_0005/meta.yaml` と `turn_0005_discarded_1/meta.yaml` の両方の値を合算しなければならない

### Requirement: ターン番号決定と discarded-dir 退避ロジックの公開ユーティリティ化
「最後に `applied` されたターン番号 + 1」を計算する次ターン番号決定ロジックと、`failed` ターンの旧 artifact ディレクトリを `turn_NNNN_discarded_<n>` へ退避するロジックは、TurnPipeline 内部にのみ閉じたコードとして実装してはならず(MUST NOT)、`add-session-autonomy` の GM review gate 事後操作から呼び出し可能な公開ユーティリティ関数として提供しなければならない(SHALL)。GM review gate の事後操作(`partial` / `edit` / `rerun_turn` 等)は TurnPipeline の8フェーズ実行そのものを経由せず、state-model の diff 適用 API とこれらの公開ユーティリティを直接呼び出す形で行われることを前提とする(D112)。

#### Scenario: rerun_turn からの公開ユーティリティ呼び出し
- **WHEN** `add-session-autonomy` が `rerun_turn` 操作のために `turn_0007` の旧 artifact ディレクトリを退避する
- **THEN** TurnPipeline が `failed` ターン再実行時に使うのと同じ公開ユーティリティ(discarded-dir 退避ロジックと次ターン番号決定ロジック)が呼び出され、`turn_0007_discarded_1` への退避が TurnPipeline の8フェーズ実行を経由せずに行われる

### Requirement: スキーマ不一致時のretry委譲
Act フェーズ等で llm-provider を呼び出した際にスキーマ検証が失敗した場合、TurnPipeline は自ら retry ループを実装せず、spec-foundation §8 に定義された llm-provider の retry(最大2回)に処理を委譲しなければならない(SHALL)。llm-provider が最終的に型付き例外を送出した場合、TurnPipeline はそのフェーズを失敗として扱い、ターンステータスを `failed` にしなければならない。

#### Scenario: llm-providerが2回のretry後も失敗する場合
- **WHEN** Act フェーズの llm-provider 呼び出しが検証失敗を繰り返し、llm-provider から型付き例外が送出される
- **THEN** TurnPipeline はそのフェーズを失敗として扱い、それまでの artifact を保存した上でターンステータスを `failed` にする

### Requirement: Checkフェーズのエラー検出による停止
Check フェーズが error 級の結果を検出した場合、commit-mode パラメータの値にかかわらず Commit フェーズでの state diff 適用を行わず、ターンステータスを `stopped_for_review` にしなければならない(SHALL)。

#### Scenario: checkerがerrorを検出する場合
- **WHEN** Check フェーズの結果に error 級の checks.yaml エントリが1件以上含まれる
- **THEN** state diff は生成されるが state-model へは適用されず、ターンステータスは `stopped_for_review` になる

### Requirement: Commitフェーズとcommit-modeパラメータ
Commit フェーズは BuildDiff スロットが生成した state diff 候補を受け取り、state-model の diff 適用インターフェースへ渡さなければならない(SHALL)。Commit フェーズ自体は diff を生成せず、BuildDiff の出力を commit-mode に従って適用するかどうかのみを決める固定ロジックである(D113)。適用するか pending にするかは、ターン実行 API 呼び出し単位のランタイムパラメータである commit-mode(`auto` | `review`)によって決まる(D118: project.yaml のフィールドにはしない)。この判断ロジックは暫定実装であり、`add-session-autonomy` によって autonomy レベル・stop condition に基づく判断へ置き換えられることを前提とする。

#### Scenario: commit-modeパラメータによる分岐
- **WHEN** Check フェーズがエラーを検出しない状態で、commit-mode パラメータが `auto` の場合と `review` の場合それぞれでターンを完了させる
- **THEN** `auto` の場合は state diff が即座に適用されてステータス `applied`、`review` の場合は適用されずステータス `pending_review` になる

