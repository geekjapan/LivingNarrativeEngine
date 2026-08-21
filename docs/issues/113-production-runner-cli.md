---
id: 113
title: CLIからchapter production runを開始・観測・停止できるようにする
status: closed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [112]
labels: [long-form, cli, production-runner]
---

# 113: CLIからchapter production runを開始・観測・停止できるようにする

## 実装内容

既存の`living-narrative book`グループに、`run-chapter`、`chapter-run-status`、`stop-chapter-run`を追加する。各commandはdomain Runnerを直接呼ぶthin adapterであり、状態遷移、LLM orchestration、budget判断をCLIへ複製しない。

成功時の出力は`ChapterProductionRunStatus`のreader-safe YAML projectionとする。CLIは本文、prompt、credential、absolute path、tracebackを出力しない。`run-chapter`に`--auto-accept`は追加しない。

## 完了条件

- [x] `book run-chapter --project P --chapter C`が同期Runnerを開始・resumeする。
- [x] `book chapter-run-status --project P --chapter C`がdurable statusを返す。
- [x] `book stop-chapter-run --project P --chapter C`がphase-boundary stop requestをdurableに記録する。
- [x] project不在・domain failureを既存CLI exit code契約で返す。
- [x] CLI出力に機密入力・prompt・credentialを含めない。

## 主な検証

`tests/cli/test_book_command.py`はstatus projection、stop request、domain Runnerへのrun delegationを検証する。
