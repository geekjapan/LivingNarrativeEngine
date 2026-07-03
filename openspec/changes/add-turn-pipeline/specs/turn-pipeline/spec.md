# turn-pipeline

## ADDED Requirements

### Requirement: フェーズ実行順序
TurnPipeline は spec-foundation §6 に定義された 8 フェーズ(Load / Intervene / Simulate / Act / Resolve / Narrate / Check / Commit)を、この順序で1ターンにつき1回ずつ実行しなければならない(SHALL)。前のフェーズが正常終了しない限り、次のフェーズを開始してはならない。

#### Scenario: mock provider による正常な8フェーズ実行
- **WHEN** mock provider・random-engine・組み込み最小スロットのみが設定されたプロジェクトで1ターンを実行する
- **THEN** Load → Intervene → Simulate → Act → Resolve → Narrate → Check → Commit の順に全フェーズが実行され、ターンステータスが `applied` または `pending_review` になる

### Requirement: スロット Protocol による差し替え可能性
Simulate / Act / Resolve / Check の各フェーズは、Protocol で定義された入出力インターフェースを持つスロットとして実装されなければならない(SHALL)。TurnPipeline はスロットの具体的な実装を知らず、レジストリ経由で注入されたスロットのみを呼び出さなければならない(D108: レジストリ辞書、plugin loader は本 change では作らない)。

#### Scenario: 組み込みスロットの差し替え
- **WHEN** 後続の change が Simulate スロットを組み込み no-op 実装から別の実装に差し替えてレジストリに登録する
- **THEN** TurnPipeline のフェーズ実行順序・呼び出しコードを変更せずに新しい Simulate 実装がそのフェーズで呼び出される

### Requirement: 組み込み最小スロット実装
本 change は次の組み込みスロット実装を提供し、mock provider のみでターンが最初から最後まで実行できるようにしなければならない(SHALL): Simulate は世界イベント候補を生成しない no-op、Act は llm-provider 経由で単一キャラクターの行動候補を1件生成する trivial 実装、Resolve は行動候補・イベント候補を乱数判定を経ずにそのまま events.yaml へ渡す pass-through、Check は checker エラーを一切検出しない no-op。

#### Scenario: 組み込みスロットのみでのend-to-end実行
- **WHEN** キャラクターが1体・シーンが1つのプロジェクトで組み込みスロットのみを使い1ターンを実行する
- **THEN** 例外を発生させずにターンが完了し、`events.yaml` に Act スロットが生成した行動由来のイベントが1件以上含まれる

### Requirement: turn artifact ディレクトリの書き込み
TurnPipeline は各ターンにつき `workspace/runs/turn_NNNN/` ディレクトリを作成し、spec-foundation §6 の表に列挙された artifact(`intervention.yaml` `agent_io/` `events.yaml` `rolls.yaml` `narration.md` `checks.yaml` `state_diff.yaml` `meta.yaml`)を書き出さなければならない(SHALL)。`turn_NNNN` の番号は spec-foundation §3 のゼロ埋め規約に従う。

#### Scenario: 全artifactの生成
- **WHEN** ターン `turn_0001` を正常に完了させる
- **THEN** `workspace/runs/turn_0001/` 配下に `intervention.yaml` `agent_io/` `events.yaml` `rolls.yaml` `narration.md` `checks.yaml` `state_diff.yaml` `meta.yaml` がすべて存在する

### Requirement: 失敗時の部分artifact永続化
いずれかのフェーズで例外が発生した場合、TurnPipeline はそれまでに生成済みの artifact を破棄せずにディスクへ保存しなければならない(SHALL)。例外を握り潰し、ターンが正常完了したかのように見せてはならない(MUST NOT)。

#### Scenario: Narrateフェーズでの例外
- **WHEN** Narrate フェーズで未捕捉の例外が発生する
- **THEN** それ以前のフェーズ(Load〜Resolve)が生成した artifact(`intervention.yaml` `events.yaml` `rolls.yaml` 等)がディスクに保存され、ターンステータスが `failed` になり、人間可読のエラーレポートが artifact に含まれる

### Requirement: meta.yaml の内容
`meta.yaml` は次の情報を含まなければならない(SHALL): フェーズごとの所要時間、LLM 呼び出し回数、使用モデル名、prompt hash の一覧、そのターンで消費した rng sequence 番号、pipeline のバージョン。

#### Scenario: meta.yamlの検証
- **WHEN** 正常完了したターンの `meta.yaml` を読み込む
- **THEN** 8フェーズ分の所要時間・LLM呼び出し回数(0以上の整数)・使用モデル名・prompt hash 一覧・rng sequence 消費数・pipeline_version フィールドがすべて存在する

### Requirement: ターンステータスモデル
TurnPipeline は各ターンの実行結果を `applied` / `pending_review` / `stopped_for_review` / `failed` のいずれか1つのステータスとして artifact に記録しなければならない(SHALL)。ステータスは全ターン artifact をスキャンすることなく、そのターンの artifact のみから判別可能でなければならない。

#### Scenario: commit-modeがauto設定でのステータス
- **WHEN** commit-mode フラグが `auto` に設定されたプロジェクトで、Check フェーズがエラーを検出せずにターンを完了する
- **THEN** ターンステータスは `applied` になり、state diff が state-model の StateStore へ適用済みである

#### Scenario: commit-modeがreview設定でのステータス
- **WHEN** commit-mode フラグが `review` に設定されたプロジェクトで、Check フェーズがエラーを検出せずにターンを完了する
- **THEN** ターンステータスは `pending_review` になり、state diff は生成されているが state-model へは未適用である

### Requirement: 次ターン番号の決定と未解決ターンによるブロック
次に実行するターン番号は「最後に `applied` されたターン番号 + 1」として決定されなければならない(SHALL)。直前のターンが `pending_review` または `stopped_for_review` の場合、それが解決される(applied または failed として確定する)まで次のターンの実行を開始してはならない(MUST NOT)。

#### Scenario: pending_reviewなターンが存在する場合のブロック
- **WHEN** `turn_0005` のステータスが `pending_review` である状態で新しいターンの実行を要求する
- **THEN** TurnPipeline は新しいターンを開始せず、`turn_0005` が未解決である旨のエラーを返す

#### Scenario: appliedなターンの後の次ターン番号
- **WHEN** `turn_0005` までのステータスがすべて `applied` である
- **THEN** 次に実行されるターンは `turn_0006` として作成される

### Requirement: スキーマ不一致時のretry委譲
Act フェーズ等で llm-provider を呼び出した際にスキーマ検証が失敗した場合、TurnPipeline は自ら retry ループを実装せず、spec-foundation §8 に定義された llm-provider の retry(最大2回)に処理を委譲しなければならない(SHALL)。llm-provider が最終的に型付き例外を送出した場合、TurnPipeline はそのフェーズを失敗として扱い、ターンステータスを `failed` にしなければならない。

#### Scenario: llm-providerが2回のretry後も失敗する場合
- **WHEN** Act フェーズの llm-provider 呼び出しが検証失敗を繰り返し、llm-provider から型付き例外が送出される
- **THEN** TurnPipeline はそのフェーズを失敗として扱い、それまでの artifact を保存した上でターンステータスを `failed` にする

### Requirement: Checkフェーズのエラー検出による停止
Check フェーズが error 級の結果を検出した場合、commit-mode フラグの設定にかかわらず Commit フェーズでの state diff 適用を行わず、ターンステータスを `stopped_for_review` にしなければならない(SHALL)。

#### Scenario: checkerがerrorを検出する場合
- **WHEN** Check フェーズの結果に error 級の checks.yaml エントリが1件以上含まれる
- **THEN** state diff は生成されるが state-model へは適用されず、ターンステータスは `stopped_for_review` になる

### Requirement: Commitフェーズとcommit-modeフラグ
Commit フェーズは Resolve/Check の結果から state diff を生成し、state-model の diff 適用インターフェースへ渡さなければならない(SHALL)。適用するか pending にするかは、プロジェクト設定の commit-mode フラグ(`auto` | `review`)によって決まる。この判断ロジックは暫定実装であり、`add-session-autonomy` によって autonomy レベル・stop condition に基づく判断へ置き換えられることを前提とする。

#### Scenario: commit-modeフラグによる分岐
- **WHEN** Check フェーズがエラーを検出しない状態で、commit-mode フラグが `auto` の場合と `review` の場合それぞれでターンを完了させる
- **THEN** `auto` の場合は state diff が即座に適用されてステータス `applied`、`review` の場合は適用されずステータス `pending_review` になる
