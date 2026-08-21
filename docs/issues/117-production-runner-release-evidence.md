---
id: 117
title: Production RunnerのE2E・benchmark baseline・release evidenceを完了する
status: closed
created: 2026-08-21
type: release
priority: P1
parent: 110
blocked_by: [112, 113, 114, 115, 116]
labels: [long-form, release, evidence]
---

# 117: Production RunnerのE2E・benchmark baseline・release evidenceを完了する

## 出荷ゲート

- [x] 全pytest回帰が成功する（`1141 passed, 2 skipped`、219.72秒）。
- [x] `ruff check .`、`ruff format --check .`、`git diff --check`が成功する。
- [x] CLI、Web API、Cockpit、fault injectionを含むv0.3.0 focused testが成功する。
- [x] `main`との差分に対するstandards/spec reviewを完了する。
- [x] release evidenceに対象commit、テスト数、static check結果、既知の運用制約を記録する。

## Review record

`main`（`4179a79aa6f19834a9247b82ab3f8aca7ccb405d`）を固定点として、AGENTS.mdのStateDiff経由・visibility維持・test-first・全check規約とIssue 111〜116の受入条件を確認した。高リスク箇所として検出した、同一本文を再生成したrevisionのcandidate/review transaction journal衝突、およびreview lifecycleでmanifest矛盾を黙って補正する経路は、release前にprovenance-aware transaction keyとfail-closed検証へ修正し、回帰テストで固定した。未解決のstandards/spec findingはない。

## Validation record

| Gate | 実行結果 |
|---|---|
| 全回帰 | `NO_COLOR=1 uv run pytest` — `1141 passed, 2 skipped in 219.72s` |
| 静的検査 | `uv run ruff check .` — 成功 |
| 整形検査 | `uv run ruff format --check .` — 285 files already formatted |
| diff整合性 | `git diff --check` — 成功 |
| Domain/CLI/Web focused | book runner、book CLI、production Web adapter、Cockpit API/UI tests — 成功 |

## 既知の運用制約

Web adapterはv0.3.0で意図的にin-process daemon threadを使用する。server再起動でthread自体は失われるが、durable artifactから`run-chapter`またはrun endpointを再実行してresumeできる。クラッシュを跨ぐworker queue、lease、outboxはv0.6.0以降のpersistent worker milestoneで扱う。
