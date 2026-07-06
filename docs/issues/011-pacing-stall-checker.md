---
id: 011
title: 物語停滞の検知と自動エスカレーションが無い(pacing/stall checker)
status: done
created: 2026-07-06
---

# 011: pacing/stall checker + 停滞時のpressureブースト

## 背景

20ターン評価の推奨#4。008/009/010で前進力学は入ったが、「前進が起きていない」ことを検知して介入する仕組みが無い。ダイスが渋い・LLMが足踏みする等で停滞したとき、現状はGMが目視で気づくしかない。

## 設計

**検知は共有ヘルパー、応答は2箇所**(checker=可視化、Simulate=自動エスカレーション)。

1. **共有ヘルパー** `detect_stall(context, window) -> int | None`(停滞ターン数 or None):
   直近 `window` ターンに以下の「前進シグナル」がひとつも無ければ停滞:
   - `threat_stage` イベント(`load_recent_events` で復元、TurnContextにpathsあり)
   - シーン遷移(scene status変更イベント / effects.scene_transition)
   - `reader_state` / `canon` の新規エントリ(`established_turn > turn - window`)
   - ※ 毎ターン出る `threat_pressure`(gm_only)と`background_event`は前進とみなさない
2. **pacing checker**(safety/、registry登録): 停滞検知時に `Finding(severity="warn", checker="pacing_check")`。warnはauto-applyを止めない(既存セマンティクス) — GM可視化のみ
3. **Simulate相の自動応答**(world_simulator): 停滞時、threatのpressureロールnotationに `+boost` を動的付加(modifierはnotation文字列埋め込み方式)+ gm_only `pacing_stall` イベントを1件発行(effectsに停滞ターン数とboost)
4. **設定**: `WorldState.pacing: PacingConfig`(`stall_window: int = 0`(0=off、後方互換)、`pressure_boost: int = 4`)。mist_station: `stall_window: 3, pressure_boost: 4`

## 完了条件

- [x] `PacingConfig` スキーマ(後方互換default、mist_station設定込み)
- [x] `detect_stall` が前進シグナル4種を正しく判定(threat_pressure/background_eventを前進と誤認しない)
- [x] pacing checkerが停滞時にwarn Findingを出し、非停滞時は沈黙。auto-applyは止まらない
- [x] Simulate相が停滞時にpressureロールへboostを付加し(roll log上notationで確認可能)、`pacing_stall` イベント(gm_only)を発行
- [x] mock全テストpass + 実LLMまたはmockで停滞→boost→stage発火加速の流れを確認(実LLMでの自然停滞待ちは不要、windowを小さくして誘発でよい)

## 関連ファイル

- `src/living_narrative/safety/registry.py:16,32,84`(Checker型・登録・defaults)
- `src/living_narrative/agents/world_simulator.py:74`(_threat_events、notation組み立て)
- `src/living_narrative/agents/event_history.py:15`(load_recent_events再利用)
- `src/living_narrative/state/models.py`(WorldState、ReaderStateEntry.established_turn)
- `src/living_narrative/session/stop_conditions.py:109`(warnはCHECKER_ERROR対象外の確認)
- 評価: `docs/evaluations/2026-07-06-replay-20turn-eval.md`
