---
id: 017
title: FactionState が定義のみで不使用(更新経路が無い)
status: done
created: 2026-07-10
---

# 017: faction state runtime

## 背景

`FactionState`(id/name/public_face/goals/resources/relations、`state/models.py:217`)はスキーマ定義・load(`store.py:62`, optional)・schema_export登録済みだが、**`WorldState.factions` へのランタイム更新経路が一切無かった**。013(関係性)・014(スレッド)以前と同じ「定義のみ・消費ゼロ」パターン。mist_stationテンプレートにも `factions.yaml` が存在しなかった。

## 実装(Threat Trackと同型)

World Simulatorは決定論的な関数(`agents/world_simulator.py`にLLMプロンプトは無い — threat_pressureもダイス駆動で、LLM生成ではない)。013計画時の「プロンプトに指針追加」という想定はここでは当てはまらないため、実装は既存の `_threat_events` パターンに素直に合わせた:

1. **イベント型追加**: `_faction_events` が毎ターン最大1派閥・1手(resources/relationsの先頭キーそれぞれ-5/+5)の `faction_move` イベントを発火(`world_simulator.py`)
2. **state_manager拡張**: `faction_move` を `StateDiff(target="faction", id=faction_id, op="delta", path="resources.<key>"|"relations.<key>")` に変換。未知faction/未知resource・relationキーは `_invalid_faction_move_reason` でreject理由付き(`state_manager.py`)
3. **diff.py**: `Target` Literalに `"faction"` 追加、`_TARGET_ATTR` に `factions` マッピング追加
4. **mist_stationテンプレート**: `templates/mist_station/state/factions.yaml` 新規(faction 1個: `faction_001` 霧守り)

## 完了条件

- [x] `faction_move` イベント型 + state_manager変換 + ガード(reject理由付き)
- [x] mist_stationに `factions.yaml`(faction 1個)追加、store.pyのoptional load経路を実際に通す
- [x] mockテスト: イベント発火・diff適用・rollback・reject系(`test_state_manager.py`/`test_world_simulator.py`/`test_state_model.py`)
- [x] 実LLMスモーク(8ターン、`sandbox/issue017_llm`、OmniRoute `auto/best-coding`)で `resources.influence` 45→5、`relations.char_001` 40→80 と実際に動くことを確認
- [x] `uv run pytest` 全件pass(697、旧689+新規8)
- [x] `uv run ruff check .` pass

## レビュー時の是正

worker初回実装は `web/server.py` のuvicorn importを遅延化する無関係な変更を含んでいた(worker自身のworktree venvに `--extra web` が未syncで発生した収集エラーの誤診断による回避策)。この変更は `test_run_server_always_binds_loopback`(`server.uvicorn` 属性へのmonkeypatchを前提)を壊しており、レビューでrevert。正しい対処は `uv sync --extra web`(環境側)。revert後、697 passed / 0 failed / 0 skippedを確認。

## 関連ファイル

- `src/living_narrative/state/models.py:217`(FactionState、変更なし)
- `src/living_narrative/state/store.py:62`(factions load、既存optional経路)
- `src/living_narrative/agents/world_simulator.py`(`_faction_events`)
- `src/living_narrative/agents/state_manager.py`(`faction_move`→diff変換、`_invalid_faction_move_reason`)
- `src/living_narrative/state/diff.py`(`Target`/`_TARGET_ATTR`にfaction追加)
- `src/living_narrative/templates/mist_station/state/factions.yaml`(新設)
- `docs/plan/feature-dag.md`(017、保留可ノード。これでTrack A完走)
