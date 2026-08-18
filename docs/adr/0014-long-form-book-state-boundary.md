# ADR-0014: 長編Book Stateの正本境界

## Context

LNE は YAML state、append-only event/roll/diff、atomic `StateDiff`、transaction
recovery を正本とし、narration を再生成可能な派生物として扱う。長編小説制作には、
作者が意図する act/章/人物弧/回収期限と、実行済み turn から観測される実績、章候補、
review decision を扱う必要がある。

既存の周辺リポジトリには章計画や story state があるが、それらを別の database、
`state.json`、UI local state、自由文 LLM output として持ち込むと、LNE の replay、
rollback、backup/restore、visibility、crash recovery の保証を失う。

## Decision

### D1: 三つの役割を分ける

- `BookPlanState` は **作者意図の正本**であり、premise、audience、act、chapter、
  required thread、character arc target、word range を持つ。
- `BookLedgerState` は **長編運用の正本**であり、active chapter、chapter lifecycle、
  observed beat、review decision、next action を持つ。
- `WorldStateBundle` と append-only event/roll/diff は **実際に起きた物語の正本**である。
  `BookPlanState` はこれを置換せず、実績を推測で書き換えない。
- chapter context、chapter candidate、quality report、manuscript は **派生物**であり、
  `workspace/books/` と turn/chapter artifact から再生成できる。

### D2: Book StateはStateStoreとtransactionの内部に置く

`BookPlanState` と `BookLedgerState` は `WorldStateBundle` の field とし、
`workspace/state/book_plan.yaml` と `workspace/state/book_ledger.yaml` に
`StateStore` が保存する。これにより state hash、commit journal、backup/restore、
rollback/recovery は既存の `commit_state_diff()` 境界に自動的に参加する。

既存 project との互換性のため、両ファイルは schema v2 では optional load とし、
欠落時は空の初期 model を得る。新規 project は空の両ファイルを作成する。旧 project
が初めて状態を commit するとき、既存transactionを通じて両ファイルを durable にする。

### D3: 更新はStateDiffだけを通す

`StateDiff.Target` に `book_plan` と `book_ledger` を追加する。book stateの変更は、
通常の turn commit、または book command が作る専用 artifact を持つ transaction を通す。
直接の YAML 書換え、UI local state の正本化、chapter text からの暗黙更新は禁止する。

`BookPlanState` の変更は structured proposal と review decision を必要とする。LLM の
自由文は proposal artifact であって state update ではない。`BookLedgerState` の
lifecycle は有限状態機械で検証する。

### D4: visibilityの原則

Book State 自体は author/GM 向けの計画情報を含むため、reader projectionに直接は出さない。
`ChapterContextBuilder` は reader-safe event と明示的に許可された plan fields だけを
writerへ渡す。`gm_vault`、`hidden_facts`、character `secrets`、`private_mind` は
BookPlan/BookLedger、chapter context、export、Web reader projectionへ複製しない。

### D5: schema versionとmigration

`CURRENT_SCHEMA_VERSION` を 2 に上げ、project schema v1→v2 migrationは
`schema_version: 2` を設定する。book stateは state file であるため project YAML
migrationでは内容を作らない。loaderのoptional defaultと、new project initializationが
この差を埋める。schema v2以降にbook state shapeを非互換変更する場合は、migration、
fixture、backup/restore、rollback、CHANGELOGを同じ変更に含める。

## Consequences

- 長編機能は LNE のtransaction/recovery seamを再利用し、二重正本を増やさない。
- `book_plan.yaml` / `book_ledger.yaml` は raw manuscriptやpromptを保存しないため、
  project stateを公開しても本文生成プロンプトを新たに露出しない。
- chapter generationのスケール、quality、UIは book state contract の後段に置く。
- 旧 v1 projectはload可能であり、book featureを使わなければ空のbook state以外の
  behaviorは変わらない。

## Rejected alternatives

- **別SQLite/JSONのBook DB:** state hash、rollback、backup/restoreと二重正本になる。
- **章原稿をcanonical stateにする:** 原稿はrenderer/model/versionに依存する派生物であり、
  event/diffより再現性が低い。
- **UIだけでchapter lifecycleを持つ:** browser refresh、branch、CLI、recovery間で一貫しない。
- **LLM自由文を直接book stateへ適用する:** 計画と実績の境界、監査、決定性を破る。
