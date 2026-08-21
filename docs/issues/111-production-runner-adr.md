---
id: 111
title: Production Runnerの実行境界と永続artifact schemaを固定する
status: closed
created: 2026-08-21
type: architecture
priority: P1
parent: 110
blocked_by: []
labels: [long-form, production-runner, recovery, architecture]
---

# 111: Production Runnerの実行境界と永続artifact schemaを固定する

## 背景

v0.2.0では、章の予約、回復可能なdraft、candidateとreviewの永続化、immutable attempt lineage、著者によるaccept/reviseが個別の安全なユースケースとして実装されている。しかし、これらを一つの章制作runとして順序どおりに実行し、停止・障害・Web server再起動後に再開する呼び出し元は存在しない。

Issue 110の完成には、HTTP requestへLLM呼出しを直接埋め込まず、Book Ledgerを一時進捗の保存先にせず、既存のdraft recoveryとtransaction境界を壊さないProduction Runnerが必要である。

## 決定する事項

Production Runnerは、同期実行可能なdomain moduleを正本の実行インターフェースとする。CLIはこのmoduleを直接呼び、Webは同一moduleへのin-process background adapterに限定する。Book chapter lifecycleはBook Ledgerに保持し、runの進捗と再開材料はBook Stateとは別のdurable artifactに保持する。

run artifactは次の配置とする。

```text
<runs>/chapter_production/
  <chapter_id>/
    generation_<plan-generation>_revision_<ordinal>/
      manifest.yaml
      request.yaml
      stop_requested.yaml     # 任意
      failure.yaml            # 任意、sanitized
      events/
        001_preparing.yaml
        002_draft_completed.yaml
        003_candidate_recorded.yaml
        004_awaiting_author.yaml
      links.yaml
```

`manifest.yaml`は現在phaseの索引であり、eventを先にatomic writeし、その後に更新する。`request.yaml`には公開可能な開始意図だけを残し、本文、prompt全文、credential、absolute path、GM-only dataは保存しない。draftのrequest/prompt/responseは既存の`runs/chapter_drafts/`を唯一の正本とし、`links.yaml`が`draft_run_id`、candidate hash、immutable attempt IDを参照する。

## 合意済みのseamとテスト対象

本Issueでは、既存の設計合意に基づき、以下をProduction Runnerの外部seamとして固定する。これらは実装詳細ではなく、呼び出し元とテストが共有するinterfaceである。

| Seam | Interface | 主な検証行動 |
|---|---|---|
| Domain production seam | `ChapterProductionRunner.run/status/request_stop` | planned/revisingからreviewまでの制作、resume、停止、矛盾のfail-closed |
| Draft recovery seam | `run_chapter_draft()` | response保存済みartifactの再利用時にproviderを再呼出ししない |
| Lifecycle seam | coordinatorのchapter transition use case | 状態更新をStateDiff transactionへ限定し、candidate/review/lineageの既存正本を再利用する |
| CLI seam | `book run-chapter`、status、stop | 一章を同期実行・観測・停止できる |
| Web adapter seam | start/status/stop HTTP endpoint | HTTP requestは即時に返り、durable statusがserver再起動後も再開可能である |

## 完了条件

- [x] CLI-first、Book lifecycleとrun phaseの分離、明示承認、phase boundary stopをADRとして記録する。
- [x] `schema_version: 1`を持つrun manifestとevent-first/manifest-second更新順を定義する。
- [x] 既存のdraft run、chapter artifacts、lineageを複製せず参照する責務分担を定義する。
- [x] run artifact、CLI、Web statusにおける非開示対象を定義する。
- [x] domain、CLI、Webの外部seamとそのTDD対象を明記する。

## 関連ファイル

- `docs/adr/0015-production-runner.md`
- `src/living_narrative/book/production_runner.py`
- `src/living_narrative/book/drafting.py`
- `src/living_narrative/book/coordinator.py`
- `src/living_narrative/web/production_run.py`
- `tests/book/test_production_runner.py`
