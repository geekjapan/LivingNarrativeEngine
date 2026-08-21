---
id: 132
title: Durable ProductionのObservabilityとRunbookを実装する
status: in-progress
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

`collect_production_operational_metrics(workspace) -> ProductionOperationalMetrics`と`render_production_runbook_snapshot(metrics) -> str`を候補seamとする。metricsはqueue/status/eventから導出するread-only projectionであり、Book Stateやauthor decisionを変更しない。

## 完了条件

- [x] queue depth、state別件数、retry countをreader-safeに集計する。
- [ ] lease age、delivery duration、sanitized failure code、budget stopをreader-safeに集計する。
- [ ] 本文、candidate本文、prompt、credential、absolute path、GM/private context、tracebackがmetrics/alert/runbookに含まれないことを固定する。
- [ ] worker kill、lease expiry、provider timeout、partial writeのtriage手順と安全なrecovery条件をrunbookへ記載する。
- [ ] thresholdとalert候補を定義し、100章fixtureのSLO測定から検証する。
- [ ] Cockpitへの投影はread-onlyで、著者のaccept/reviseを自動化しない。

## 非対象

外部SaaS telemetry、credentialを要するalert delivery、private prompt/本文のログ収集、auto-accept/auto-reviseは対象外である。
