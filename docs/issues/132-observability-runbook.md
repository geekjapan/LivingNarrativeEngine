---
id: 132
title: Durable ProductionのObservabilityとRunbookを実装する
status: completed
created: 2026-08-21
type: feature
priority: P1
parent: 132
blocked_by: [129, 130, 131]
labels: [long-form, production, observability, privacy, operations]
---

# 132: Durable ProductionのObservabilityとRunbookを実装する

## 背景

durable workerを運用するには、queue depth、lease age、delivery duration、retry、cost stop、failure taxonomyをreader-safeに観測し、worker kill・lease expiry・provider timeout・partial write時に一貫してtriageできる必要がある。

## 公開seam

`collect_production_operational_metrics(project_yaml) -> ProductionOperationalMetrics`と`render_production_runbook_snapshot(metrics) -> str`を公開seamとする。metricsはqueue/status/eventから導出するread-only projectionであり、Book Stateやauthor decisionを変更しない。

`queue.delivery_duration_*`はqueue eventの`leased`から`completed`または`failed`までの公開timestampを集計した値である。`budget_stops`はproduction runの`stop_requested.yaml`で`source: budget`と明示されたものだけを数え、自由文reasonを固定taxonomyへ正規化する。

## 完了条件

- [x] queue depth、state別件数、retry countをreader-safeに集計する。
- [x] active leaseの最古heartbeat ageをworker identityなしでreader-safeに集計する。
- [x] sanitized failure code別件数をdetail・worker identityなしでreader-safeに集計する。
- [x] delivery duration、budget stopをreader-safeに集計する。
- [x] 本文、prompt、absolute path、worker identity、traceback detailがmetrics/runbook snapshotに含まれないことを固定する。
- [x] candidate本文、credential、GM/private contextについても、budget stop artifactの自由文reasonを公開taxonomyへ正規化して非漏洩を回帰テストで固定する。
- [x] worker kill、lease expiry、provider timeout、partial writeのtriage手順と安全なrecovery条件をrunbookへ記載する。
- [x] thresholdとalert候補を定義し、100章fixtureのSLO測定から適用範囲を検証する。
- [x] queue metricsを`ProductionOperationalMetrics`とpath-free runbook snapshotへread-only投影できる。
- [x] Cockpitへの投影はread-onlyで、著者のaccept/reviseを自動化しない。

## 閾値・alert候補

| 信号 | 候補となる判定 | 運用アクション | 自動化しない理由 |
|---|---|---|---|
| 100章benchmark `duration_slo` | `max_duration_ms = 10,000`を超過 | CIをfailureにし、artifact/index/fixtureの回帰を調査する | provider非呼出の構造的quality gateであり、本文品質や実LLM遅延を表さない |
| `queue_delivery_duration_max_ms` | baseline取得後に同一provider profile内の異常値を検知する | worker/lease/run manifestをreader-safe情報だけでtriageする | 実LLM時間はprovider・モデル・ネットワークで変動するため、v0.8.0では固定閾値を置かない |
| `budget_stop_total` | `0`より大きい | cost policyまたはattempt policyを著者・運用者が明示的に確認する | budget stopは失敗ではなく、著者判断を待つ保護状態である |
| `oldest_lease_age_seconds` | configured lease expiryに近づくか超過する | lock取得可否を確認し、expiry後のみ安全に再配送する | worker identityやprivate実行詳細を公開しない |

100章fixtureで観測したbenchmark本体約35 msとCI SLO 10,000 msの差は、CI揺らぎを吸収しつつ桁違いの回帰を検出するための余白である。この値をactual delivery durationへ流用しない。

## 非対象

外部SaaS telemetry、credentialを要するalert delivery、private prompt/本文のログ収集、auto-accept/auto-reviseは対象外である。
