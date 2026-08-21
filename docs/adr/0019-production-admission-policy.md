# ADR-0019: Production Admission Policy（book間並列・provider rate limit・USD予約）

## Context

ADR-0018で、単一Bookにおけるchapter productionの重複実行は、durable queue、POSIX lease、heartbeat、fencing generationによって防止された。しかし、複数Bookを同時に制作する運用では、各Bookのqueueだけでは、provider profileごとの呼出頻度、全体の同時delivery数、未確定のprovider利用額を一貫して制御できない。

既存の`CostPolicyV2`は、chapter、act、bookごとのUSD preflightを評価するreader-safeな純粋modelであり、`collect_book_usage`は完了済みrunからactual/estimated USDを集計する。一方、同時に開始したdeliveryの見積額はまだactual usageに含まれないため、book hard capを超過して予約できる余地がある。これを防ぐため、queue leaseとは別に、複数Bookで共有できるadmission制御点が必要である。

## Decision

### D1: admissionの責務をqueue leaseから分離する

`DurableProductionQueue`はBook内のjob順序、idempotency、lease、worker recoveryを引き続き唯一の責務とする。book間policyは、新しい`ProductionAdmissionController` moduleが担う。外部seamは、次の小さいinterfaceとする。

```python
try_admit(request: ProductionAdmissionRequest) -> ProductionAdmissionDecision
release(lease: ProductionAdmissionLease, outcome: ProductionAdmissionOutcome) -> None
```

queue jobはadmissionが許可された後にだけrunnerを起動する。admissionが拒否されたqueue jobはterminal failureにせず、同じidempotency keyを保って`queued`へ戻す。したがって、rate limit又はbudgetの一時的な不足はreview・author approval・chapter lifecycleを変更しない。

### D2: shared scheduler namespaceは明示設定する

複数Bookを横断する制御対象は、`scheduler_root`で明示されるscheduler namespaceに限る。既定で暗黙のマシン全体ディレクトリを作成しない。複数のprojectが同じbook間parallel上限、provider rate limit、USD予約を共有したい運用者は、同一の`production_admission.scheduler_root`を設定する。

namespace配下のsnapshotとappend-only eventはatomic YAMLで保存し、更新・読込とも専用lockで排他する。snapshotにworkspace path、本文、prompt、credential、worker identity、tracebackを保存しない。Book識別子は、scheduler namespace内だけで使う不可逆のworkspace fingerprintとする。

### D3: provider profileとrate limitは決定的に識別する

admission requestは、projectの解決済みLLM bindingから得るprovider profile ID、予約対象のrequest count、実行開始時刻を持つ。rate limitはsliding-windowではなく、durable eventの時刻を用いるfixed-window又はrolling timestamp集合で評価し、テストでは注入可能なclockで決定性を保つ。

provider profile IDはprofile名又は設定済みのreader-safe IDだけで構成する。base URL、API key、prompt内容、本文をprofile ID又はeventへ含めない。

### D4: book hard USD capにはactual + active reservationを用いる

book scopeにhard USD capがある場合、admissionは次を合算して判定する。

1. `collect_book_usage`から得たreader-safeなactual USD。ただしactual USDが不明ならfail closedとする。
2. 同じBook fingerprintに対する未解放reservation USD。
3. 今回requestのforecast USD。

合計がhard capを超える、又はhard capがあるのにprice snapshot、estimate、actual evidenceのいずれかが不明な場合、admissionは拒否する。soft capは既存のwarning契約を維持し、admissionがhard-stopをsoft warningへ弱めない。

reservationはrunner完了・sanitized failure・queue deferralのすべてで必ず解放する。process crash後のlease expiryでは、admission snapshotのexpiryを通じて再claim可能にする。同じqueue deliveryのfencing generationをreservation keyへ含め、古いworkerが新しいreservationを解放できないようにする。

### D5: Cockpitはreader-safeなread-only投影だけを行う

Cockpitとrunbookには、active admission数、configured cap、providerごとのdeferred count、予約USD合計、budget-blocked count、oldest admission ageといった集計だけを投影する。providerの秘密設定、workspace path、job ID、本文、prompt、著者のprivate contextは投影しない。policyは著者の`accept`/`revise`を自動化しない。

## Consequences

v0.7.0では、`ProductionAdmissionPolicy`、durable shared snapshot/events、book間parallel上限、provider profile rate limit、book hard USD reservation、queue deferral/recovery、reader-safe metricsを一つのvertical sliceとして実装する。Book内serial lease、StateDiff経由のBook State mutation、explicit author reviewは変更しない。

scheduler namespaceを明示設定しない既存projectは、v0.6.0と同じ単一Book queue挙動を継続する。これによりmigrationを不要にし、新fieldはdefaultで後方互換とする。global broker、分散clock同期、外部SaaS telemetry、provider APIからのlive quota取得、auto-accept/auto-reviseは対象外とする。

## Status

accepted
