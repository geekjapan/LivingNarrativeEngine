# Durable Production Recovery Runbook

## 目的

このrunbookは、chapter production workerの異常時に、**Book Stateを直接変更せず**、既存のdurable run artifact・queue artifact・著者の明示accept/revise契約を保ったまま制作を回復するための手順である。queueは本文、prompt、credential、GM/private contextを保存しない。そのため、調査・共有・チケットに記録してよいのはqueue state、chapter ID、run ID、phase、delivery count、lease age、sanitized failure code、公開timestamp、集計済みdelivery duration、正規化済みbudget stop taxonomyだけである。

## 事前確認

最初に対象workspaceの`project.yaml`を特定し、Cockpitまたは`book chapter-run-status`でchapterのreader-safe statusを確認する。状態YAML、BookPlan、BookLedger、candidate、accepted attemptを手作業で書き換えてはならない。著者のaccept/reviseを自動化してはならない。

| 事象 | 安全な判定材料 | 禁止事項 |
|---|---|---|
| worker kill | job lock解放、lease expiry、同一chapterのrun artifact | 新しいgenerationやcandidateの手作業作成 |
| lease expiry | lease timestamp、job lock取得可否、sanitized status | lockが残るjobの強制再配送 |
| provider timeout | sanitized failure code、既存manifest/response artifact | prompt・本文・tracebackの収集や共有 |
| partial queue write | queue schema validation error、append-only event | YAMLの手修正による黙示的修復 |
| delivery durationの異常 | `queue_delivery_duration_count`、`queue_delivery_duration_max_ms`、queue state | worker IDや本文を含む詳細traceの収集 |
| budget stop | `budget_stop_total`、正規化reason code、cost policyのpublic設定 | 自動再予約、auto-accept、自由文stop reasonの共有 |

## Worker kill / lease expiry

workerが停止した場合、直ちに別workerで同じchapterを開始してはならない。job lockがOSによって解放され、leaseが期限切れになった後にのみworkerは同じidempotency keyをclaimできる。claim成功後、workerは同じ`ChapterProductionRunner`を呼び、既存manifestからresumeする。すでにdurable response artifactが存在する場合、Runnerはproviderを再呼出しせずに回復する。

> 期限切れは再配送の必要条件であり、十分条件ではない。POSIX job lockを取得できない場合は、元workerがまだ実行中である可能性があるため、再配送しない。

## Provider timeout / sanitized failure

timeoutなどの失敗はqueueの`failure_code`とRunnerのsanitized statusで確認する。原因調査後に著者または運用者が同じchapterを明示的に再予約すると、同じidempotency keyとjob IDがqueuedへ戻る。retryはBook Stateを変更せず、Runnerの既存recovery規約に委譲する。budget hard-stopまたは著者のstop requestがある場合は、再予約せず、著者の判断を待つ。

## Delivery duration / budget stop

`collect_production_operational_metrics(project.yaml)`またはCockpitのread-only operationsで、`queue_delivery_duration_count`、`queue_delivery_duration_total_ms`、`queue_delivery_duration_max_ms`、`budget_stop_total`を確認する。durationはqueueの`leased`からterminal `completed`または`failed`までの公開timestampに基づくaggregateであり、実LLMの本文品質や著者レビュー時間を測るものではない。

budget stopは`source: budget`のdurable stop artifactだけを数え、公開値は`chapter_attempt_limit`、`book_attempt_limit`、`consecutive_revision_limit`、`chapter_hard_usd_limit`、`book_hard_usd_limit`、`other_budget_policy`に正規化される。`budget_stop_total > 0`はcostまたはattempt保護が動作したことを示すため、再予約・accept・reviseを自動実行してはならない。著者または運用者がreader-safe cost policyとchapter lifecycleを確認し、明示操作を選ぶ。

100章provider非呼出benchmarkの`10,000 ms`はCIの構造的quality gateであり、actual delivery durationのalert閾値ではない。actual delivery durationはprovider profileごとの十分なbaseline取得後に、reader-safe aggregateだけで異常を検討する。

## Partial queue write / schema corruption

queue snapshotまたはevent artifactがschema不正なら、queueはfail closedする。YAMLを直接補正してclaimを再開してはならない。まずworkspaceを保全し、corrupt artifactのhashとreader-safe metadataだけを記録する。既存run manifest・chapter lineage・Book Stateが健全であることを確認したうえで、専用のmaintenance recovery手順または実装修正を介して復旧する。壊れたqueueを黙って空にすることは、delivery監査とat-least-once recoveryを失わせるため禁止する。

## エスカレーション条件

次の場合は自動retryを行わず、著者またはリードエンジニアへエスカレーションする。

- queue corruptionが検出された場合。
- leaseが期限切れでもjob lockが解放されない場合。
- 同一chapterでsanitized failureが繰り返される場合。
- budget hard-stop、author stop、またはreview待ちstatusがある場合。
- `budget_stop_total`が増加したが、著者または運用者の明示判断が記録されていない場合。
- provider profileごとのbaselineに対してdelivery durationの異常が疑われるが、queue/manifestだけでは安全に原因を確定できない場合。
- 意図しない本文、prompt、private data、credential、absolute pathがpublic artifactまたはmetricsへ出現した疑いがある場合。

## 記録形式

インシデント記録には、発生時刻、workspaceを識別しない運用チケットID、chapter ID、queue state、run ID、phase、delivery count、lease age、sanitized failure code、集計済みdelivery duration、正規化済みbudget stop reason code、実施した明示操作、著者判断を記載する。本文、candidate本文、prompt、provider response全文、traceback、credential、GM/private context、absolute path、自由文stop reasonを貼り付けない。
