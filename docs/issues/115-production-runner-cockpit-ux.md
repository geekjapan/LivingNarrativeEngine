---
id: 115
title: Cockpitへchapter production runの操作・進捗・resume表示を追加する
status: closed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [114]
labels: [long-form, web, cockpit]
---

# 115: Cockpitへchapter production runの操作・進捗・resume表示を追加する

## 実装内容

単一ページCockpitを既存の`/start`操作から新しい`/run` APIへ移行する。章ごとのreader-safe run statusを取得して、phase、停止理由、failure code、resume状態を表示する。実行中には停止ボタンを表示してstatus pollingを有効にし、stopped lifecycleでは同じrunを再開できる操作を表示する。

既存のaccept/revise操作はreview lifecycleだけに残し、著者の明示承認を維持する。`cockpit.can_operate`がfalseの閲覧モードではrun、stop、accept、reviseのmutation controlを生成しない。動的な文字列はすべて`escapeHtml`を経由し、run statusで追加した文字列も例外としない。

## 完了条件

- [x] planned/revisingにrun開始、実行中に進捗・停止、stoppedにresumeを表示する。
- [x] reviewに既存の承認・改稿操作だけを表示する。
- [x] non-authoring modeではmutation controlを表示しない。
- [x] runが進行中のときだけCockpit pollingを有効にする。
- [x] UIはprompt、本文、credential、absolute pathを表示しない。
- [x] page XSS regression testが動的run statusを含めて通過する。

## 主な検証

`tests/web/test_web_app.py`はHTML contract、run/stop endpoint使用、動的HTMLのescapeを検証する。
