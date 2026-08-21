---
id: 114
title: Web background adapterとchapter production APIを実装する
status: closed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [112]
labels: [long-form, web, production-runner]
---

# 114: Web background adapterとchapter production APIを実装する

## 実装内容

`web.production_run`に、CLI-firstの`ChapterProductionRunner`を同一プロセス内daemon threadで呼び出すadapterを追加する。thread registryは実行中フラグの表示と二重開始防止だけに使用し、回復の正本はdomain Runnerのdurable artifactである。Web server再起動後も同じchapter run endpointを呼ぶことでresumeできる。

HTTP APIは以下を提供する。

| Endpoint | 成功 | 用途 |
|---|---:|---|
| `POST /api/project/{name}/book/chapters/{id}/run` | 202 | production runの開始またはresume |
| `GET /api/project/{name}/book/chapters/{id}/run` | 200 | reader-safe statusの取得 |
| `POST /api/project/{name}/book/chapters/{id}/run/stop` | 202 | durable phase-boundary stopの要求 |

開始と停止はauthoring modeに限定し、読み取りは既存Cockpitと同じsensitive session access境界に従う。routeは状態を持たず、例外を404または409へ変換するだけとする。

## 完了条件

- [x] in-process adapterが二重開始を409相当で拒否する。
- [x] statusはthread進行中とdurable statusを統合してreader-safeに投影する。
- [x] stopは強制cancelではなくRunnerのdurable stop requestへ委譲する。
- [x] start/status/stop APIが202/200/202の契約を満たす。
- [x] non-authoring modeはすべてのmutation endpointで403となる。

## 主な検証

`tests/web/test_production_run.py`はthread registryと完了status投影、`tests/web/test_book_cockpit_api.py`は202 payloadと権限境界を検証する。
