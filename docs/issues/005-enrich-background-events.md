---
id: 005
title: mist_stationの背景イベントテーブルを充実させる
status: done
created: 2026-07-06
---

# 005: 背景イベントテーブル充実

## 背景

World Simulatorは設計通り重み付きテーブル抽選(`world_simulator.py:34`、LLM不使用)。ターン1の背景イベントが平板だったのはテーブルの中身が薄いため(所見#5、軽微)。

## 完了条件

- [x] `mist_station` テンプレートの `background_events` テーブルのエントリを増やし、文章の質を上げる(日本語、雰囲気のある描写、シーンの霧・駅の設定と噛み合うもの)
- [x] 重み配分を見直し(稀な不穏イベント vs 日常的な環境描写)
- [x] mist_run_001 で数ターン回して単調にならないことを確認(verify-005で8ターン: 5種、全てテーブル由来、leak findingsゼロ)

## 実装メモ

テーブルは実際には `world_simulator.py` にハードコードだった(テンプレートに無し)。`WorldState.background_events`(optional、`BackgroundEventTableEntry`)としてデータ化し、空なら旧2エントリへフォールバック。simulatorの抽選挙動は不変。

## 関連ファイル

- `src/living_narrative/templates/`(mist_station)
- `src/living_narrative/agents/world_simulator.py:34`(挙動は変えない — データのみ)
