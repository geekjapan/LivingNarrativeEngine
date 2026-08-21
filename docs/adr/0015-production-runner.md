# ADR-0015: Chapter Production RunnerのCLI-first実行とdurable run artifact

## Context

長編制作では、章の予約、回復可能な本文draft、candidate/reviewの品質評価と永続化、immutable attempt lineage、著者のaccept/reviseを順序どおりに実行する必要がある。v0.2.0ではそれぞれが独立した安全なユースケースとして存在するが、Cockpitから開始された章を`review`まで進めるproduction callerは存在しない。

この不足を単一のHTTP requestで補うと、LLM呼出しの長時間化、request timeout、Web server再起動、部分artifact、budget block、author decisionの責務が混ざる。さらに、runnerの細かな進捗をBook Ledgerに追加すると、制作上の正本lifecycleと一時的な実行状態が混同され、StateDiff transactionの責務が不明瞭になる。

## Decision

### D1: CLI-firstのdomain runnerを唯一の制作orchestration moduleとする

`book.production_runner.ChapterProductionRunner`を、章制作を同期実行・再開・停止要求する唯一のdomain moduleとする。公開interfaceは`run(project_yaml, chapter_id, *, gateway, budget)`、`status(project_yaml, chapter_id)`、`request_stop(project_yaml, chapter_id)`の三つに限定する。

CLIはRunnerを直接呼び出す。WebはRunnerを呼ぶin-process background adapterに限定し、HTTP routeは開始、durable status取得、停止要求だけを公開する。HTTP handlerにdraft、compile、review、StateDiff mutationを直接実装しない。

Web server再起動時にin-process threadは失われ得る。この制約はv0.3.0で受容し、次回のCLIまたはWeb開始がdurable artifactから同じrunをresumeすることで回復する。persistent queue、別host worker、複数workerはv0.6.0以降の責務とする。

### D2: Book lifecycleとrun phaseを分離する

`BookChapterLedger.lifecycle`は、章が制作上どこにあるかを表す唯一の正本とする。Runnerは既存coordinatorの`start_chapter_production()`、`record_chapter_candidate()`、`open_chapter_review()`を通じてのみlifecycleを変更し、直接YAMLを書き換えない。

Runnerの進捗は`runs/chapter_production/<chapter-id>/generation_<generation>_revision_<ordinal>/manifest.yaml`に保持する。run manifest schemaは`schema_version: 1`を持ち、phase、run identity、公開可能なtimestamp、resume observationだけを保持する。Book State schemaに`active_run_id`を追加しない。

| 正本・artifact | 保持する事実 | Runnerの扱い |
|---|---|---|
| Book Ledger | `planned`、`running`、`candidate`、`review`、`accepted`、`revising` | coordinatorのStateDiff transactionだけで更新する |
| Run manifest/events | 一つのrunのphase、再開・停止・failureの観測 | eventを先に書き、manifestを後から索引として更新する |
| Draft run artifact | request、prompt、response、calls、meta、provider failure | `draft_run_id`で参照し、Runnerは複製しない |
| Chapter artifacts / lineage | candidate、review、immutable attempt、accepted pointer | coordinatorが保存し、Runnerはidentityをlinksへ参照記録する |

### D3: Runnerはreviewまで自動化し、著者の明示承認を必須とする

Runnerはdraft、compile、semantic continuity評価、deterministic review、candidate記録、review openまでを実行する。`review`到達時のphaseは`awaiting_author`とし、Runnerは終了する。

accept/reviseは既存のauthor actionだけが実行する。`--auto-accept`、reviewを無視するauto-revise loop、未検証本文のmanuscript exportはv0.3.0に含めない。この決定により、accepted artifactだけが原稿化対象という既存の契約を維持する。

### D4: stopはdurableに記録し、phase boundaryでのみ適用する

停止要求はrun rootの`stop_requested.yaml`にdurableに記録する。Runnerはdraft開始前、draft完了後、candidate記録前、review開始前でこれを確認する。停止を観測した場合は`stopped` phaseとsanitizedな理由をevent-firstで記録し、Book lifecycleの正当な状態を推測で変更しない。

provider呼出し中の強制cancelは行わない。response/meta書込み順とdraft recoveryを壊す可能性があるためである。停止後の再開は同一run artifactから可能とし、responseが存在するdraftはproviderを再呼出ししない。

### D5: 矛盾はfail closedとし、run artifactから正本を再構成しない

manifest phaseとBook lifecycle、candidate/review、lineageの組み合わせが許容されない場合、Runnerはmutationを行わず`failed` phaseとsanitizedなfailure codeを記録する。矛盾を黙って補正してはならない。修復には既存transaction recoveryまたは将来の明示repair flowを用いる。

### D6: 非開示情報をrun statusとartifactから除外する

run manifest、event、failure、CLI出力、HTTP response、Cockpit投影には本文、prompt全文、credential、absolute path、`gm_vault`、`hidden_facts`、character secret、`private_mind`、tracebackを保存・返却しない。provider詳細failureはdraft artifact内の既存方針に留め、Runnerのpublic failureは固定したsanitized codeへ写像する。

## Consequences

この決定により、CLI、Web、将来のpersistent workerは同じ深いRunner moduleを再利用できる。callerは3操作だけを学べばよく、draft recovery、lifecycle transition、attempt provenance、phase artifact、停止・failure処理の複雑性をRunner内部へ局所化できる。

一方、v0.3.0のWeb実行はserver再起動中に生きたthreadを保持しない。また、stopはprovider呼出しを即時中断しない。Cockpitはdurable statusを真実として表示し、再開可能性を明示する必要がある。

## Rejected alternatives

- **HTTP handler内の同期LLM orchestration:** request timeout、重複実行、障害時の再開責務がrouteへ拡散する。
- **Book Ledgerにrun phaseやactive run IDを追加:** 正本lifecycleと一時進捗を混ぜ、v0.3.0のためにschema migrationを導入することになる。
- **Web threadをrunの正本にする:** server再起動とCLI実行を跨いで状態を復元できない。
- **未検証candidateのauto-accept:** 著者の明示決定とaccepted attemptのみを原稿化する契約を破る。
- **provider呼出しの強制停止:** request/prompt/response/metaの回復順序を破り、二重生成または監査不能なpartial artifactを生む。
- **矛盾の暗黙repair:** candidate、review、lineageのどれを正本とするかを恣意的に選ぶことになる。
