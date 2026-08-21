# ADR-0018: Durable Production QueueとLease付きWorker

## Context

v0.5.0までの章制作は、`ChapterProductionRunner`を唯一のdomain orchestration moduleとし、Webはdaemon threadでこれを起動している。このthreadは実行上の便宜であり、run manifestはdurableである一方、HTTP server、sandbox、またはprocessが停止すると実行者自体は失われる。数十万文字級の長編を100章規模で制作するには、HTTP requestの寿命から実行を分離し、停止後も同じ制作runを安全に再配信できる実行基盤が必要である。

既存Runnerは、同一run artifactからのresume、responseを永続化済みのdraftのprovider非再呼出し、candidate/review/lineageを通じた著者の明示accept、phase boundaryでのstop、sanitizedな公開statusを既に担う。queue/workerはこれらを再実装せず、Runnerの前段でdeliveryを耐久化する。

## Decision

### D1: queue backendはworkspace内のatomic YAML snapshotとappend-only public event artifactにする

queue正本は`runs/chapter_production_queue/queue.yaml`に保存する。payloadはschema-validatedなjob metadataだけとし、atomic replaceとdirectory fsyncでpublishする。jobの遷移は同じrootのevent artifactへ先に追記し、queue snapshotを後から索引として更新する。外部broker、database、credential、本文、prompt、provider responseは導入しない。

このbackendは単一workspace filesystemをfailure domainとする。queue snapshotまたはevent artifactがschema不正・不整合の場合はclaimせずfail closedする。状態YAML（BookPlan/BookLedger）の変更はこれまでどおりCoordinatorの`StateDiff` transactionだけが行い、queue artifactはBook Stateの正本ではない。

### D2: idempotency keyはBookPlan generation・chapter・revisionで決定する

enqueueは`generation:chapter_id:revision`から決定的なidempotency keyを作る。同じkeyのqueuedまたはleased jobは新規jobを作らず、既存jobを返す。worker restart後のdeliveryも同じkeyを使用する。実制作のrun identity、draft recovery、candidate lineageは既存`ChapterProductionRunner`が唯一決定する。

### D3: workerはjob lockとrenewable leaseを併用する

claimはworkspace project lockの下でqueue snapshotを更新し、jobごとのPOSIX advisory lockを獲得できたworkerだけにleaseを与える。leaseは`worker_id`、fencing generation、heartbeat timestamp、expiryをreader-safe metadataとして記録する。workerはRunner実行中にheartbeatを更新する。

lease expiryだけでは、停止したworkerが再び動き出す可能性を排除できない。そのため、次のworkerはexpiry後であってもjob lockを獲得できなければRunnerを起動しない。worker processがkillされたときはOSがjob lockを解放し、次のworkerがexpired jobをclaimして同じRunnerをresumeできる。これによりat-least-once deliveryを提供しながら、同時Runnerによる二重draft・二重candidate・二重acceptを防ぐ。

### D4: workerはRunnerを一度だけ呼ぶ深いmoduleとする

外部callerが学ぶinterfaceは次の三つに限定する。

| Interface | 責務 | 非責務 |
|---|---|---|
| `DurableProductionQueue.enqueue(project_yaml, chapter_id)` | idempotentなjob予約と公開projection | 本文生成、Book State mutation |
| `DurableProductionQueue.status(project_yaml, chapter_id)` | queueとRunner manifestを合成したreader-safe status | prompt/本文の返却 |
| `DurableProductionWorker.run_once(project_yaml, worker_id)` | 一件claim、heartbeat、Runner実行、completionの記録 | accept/revise、scheduler policy |

workerは`ChapterProductionRunner.run()`を一度だけ呼び、その戻り値またはsanitized failureをjobへ記録する。著者のaccept/reviseはworkerの外に残す。既存Runnerのdurable artifactsがrecovery source of truthであり、queueがBook lifecycleを推測・修復してはならない。

### D5: observabilityはpublic metadataに限定する

queue job・lease・eventに保存できるのはidempotency key、chapter ID、run ID、phase、attempt count、duration、sanitized failure code、timestamp、worker IDのhashまたはopaque IDだけとする。本文、candidate本文、prompt全文、credential、absolute path、`gm_vault`、`hidden_facts`、character secret、`private_mind`、tracebackは保存もmetrics送信も禁止する。

### D6: retentionとfailure domainを明示する

terminal jobとeventは同一generation内で監査・benchmark・resume観測に必要な期間保持する。pruneは後続の明示maintenance operationでのみ許可し、active/leased jobを削除してはならない。worker kill、lease expiry、provider timeout、partial queue writeはfault injectionの対象とし、queueは復旧できない状態を黙って補正しない。

## Consequences

Web requestはjobをenqueueして202を返せるようになり、CLIまたは別processのworkerが実制作を実行する。HTTP server restartはjobを失わせず、worker kill後はlease expiryとjob lock解放後に同一idempotency keyを再配信できる。Book内serial、book間parallel、provider rate limit、budget reservation、100章index/SLO、metrics/alert/runbookは後続Issueでqueue coreの上に実装する。

YAML queue backendは単一filesystemを跨ぐdistributed brokerではない。異なるhostまたはobject storage上の同一workspaceでの共有は保証しない。これはv0.6.0のlocal/persistent worker failure domainを明示するトレードオフであり、将来backend adapterが二つ以上必要になった時点でinterfaceを抽象化する。

## Rejected alternatives

- **Web daemon threadをqueueの正本にする:** HTTP server restartでlease・delivery・heartbeatを失う。
- **Runnerをqueue workerへ複製する:** draft recovery、StateDiff lifecycle、review/authoring契約が二重化する。
- **lease expiryだけで第二workerを起動する:**停止したworkerが再開した際に同時Runnerが発生し得る。
- **Book Ledgerへqueue/lease fieldを追加する:**制作lifecycleと実行配信状態を混同し、migrationと回復責務を増やす。
- **本文またはpromptをjob payloadへ入れる:**queue persistenceとobservabilityへprivate contextを拡散する。
- **auto-acceptまたはauto-revise:**著者の明示accept/reviseとaccepted attemptのみを原稿化する既存契約を破る。
