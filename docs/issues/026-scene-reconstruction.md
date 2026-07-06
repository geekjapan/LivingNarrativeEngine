---
id: 026
title: scene reconstruction + 重要イベント抽出(Export基盤、Track C起点)
status: done
created: 2026-07-07
---

# 026: scene reconstruction + event抽出

## 背景

DAG Track C起点。Phase 6「セッションログからシーン一覧を作れる」。009でシーンはstate上の一級市民になり、遷移・summary・timelineが揃ったため、**シーン再構成はLLM不要の決定論**で組める。027(章立て/novel draft)/028(TRPGリプレイ強化)/029(arcレポート)の共通基盤。

## 設計

1. `export_replay/`(既存module)に `reconstruction.py`: `reconstruct_session(project_path) -> SessionReconstruction`
   - **SceneRecord**: scene id/location/mood/summary(最終値)、開始ターン・終了ターン(scene status遷移diffから復元。scene_001は turn 1 開始)、参加キャラ推移
   - **key_events**(シーンごと、reader可視中心): threat_stage(reader/scene可視)、scene遷移、reveal系、thread_update(open/advance/resolve、gm_onlyだが構成情報として保持しvisibilityタグ付き)、character_death等の重イベント。背景イベント・毎ターンのthreat_pressureは除外
   - **turning_points**: pressure閾値到達ターン、シーン遷移ターン、review停止ターン
   - metrics(019 session/metrics.py)と重複する集計はimportして再利用
2. CLI: `living-narrative export --format scenes`(既存exportサブコマンドの形式追加 or `--scenes` フラグ — 既存export実装の流儀に合わせる)。出力: `exports/scenes.yaml` + 人間可読の `scenes.md`(シーン見出し+期間+summary+key_eventsリスト)
3. reader可視版とGM版(gm_only込み)の2モード(`--gm`)。デフォルトはreader版(replay export同様、D120のreject_allターン除外規則に従う)

## 完了条件

- [x] mockプロジェクト(遷移込み)で scenes.yaml/scenes.md が正しく出る(シーン2つ・ターン範囲・key_events)
- [x] reader版にgm_only情報が混入しない/GM版には入る(テスト)
- [x] 019 metricsとの整合(重複ロジックなし、再利用)
- [x] mock全テストpass(620+)
- [x] 実データ確認: `sandbox/bench20_llm` でexport(--gm)。2シーン・ターン範囲1〜14/14〜継続中・key_events時系列・転換点(stage発火4点)すべて妥当。物語の骨格が一目で読める出力

## 関連ファイル

- `src/living_narrative/export_replay/`(既存replay exporter)/ `cli/export.py`
- `src/living_narrative/session/metrics.py`(再利用)
- `sandbox/bench20_llm/`(実データ検証用、20ターン・遷移・5スレッド)
- DAG: `docs/plan/feature-dag.md`
