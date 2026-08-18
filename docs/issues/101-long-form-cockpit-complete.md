---
id: 101
title: 長編制作Web Cockpit完全実装
status: in_progress
created: 2026-08-18
---

# 長編制作Web Cockpit完全実装

## 背景

初期CockpitはBookPlanと章開始の読取り・操作を提供するが、candidate/review/accept/revise、attempt履歴、quality block、budget停止、manuscript exportを一連の安全な操作として扱えない。

## 完了条件

| 条件 | 判定方法 |
|---|---|
| chapter lifecycle、next action、quality block、budget状態、attempt一覧をread APIで投影する | API integration test |
| running/candidate/review/revisingに対する許可操作だけをmutation APIへ公開する | lifecycle API test |
| accept/reviseは保存済みreviewとlineageを必ず検証する | invalid transition test |
| player_character sessionではCockpit全体を非表示かつAPIを403にする | permission/UI test |
| UIは本体・attempt・review理由・開始可能な操作を安全に描画する | UI contract/XSS test |
| UI操作後にCockpit投影が再読込される | browser/API integration test |

## 関連ファイル

- `src/living_narrative/web/app.py`
- `src/living_narrative/web/service.py`
- `src/living_narrative/web/page.py`
- `src/living_narrative/book/cockpit.py`
- `tests/web/test_book_cockpit_api.py`
- `tests/web/test_web_app.py`

## 非対象

Webからの任意provider key入力、リアルタイム協働編集、サーバ常駐キューは扱わない。
