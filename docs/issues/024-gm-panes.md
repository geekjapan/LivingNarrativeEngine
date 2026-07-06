---
id: 024
title: Web UI — GM Panes(キャラクター/世界/タイムライン全可視ペイン)
status: done
created: 2026-07-07
---

# 024: GM Panes(Track B、020の続き)

## 背景

DAG Track B(`docs/plan/feature-dag.md` Track B行、024番)。既存の `/status` などはリーダー/プレイヤー向けの漏洩防止フィルタを常にかける(spec-foundation.md §4)。GMは本来全情報(secrets/private_mind/hidden_facts/gm_only visibility含む)を見られるべきだが、そのための専用ペインがまだ無い。「GMコックピット」の可視化面を完成させる。

## 設計

**API**(`web/service.py` / `app.py`、すべて読み取り専用・FastAPI-free な service層):

1. `GET /api/project/{name}/gm/characters` — 全キャラクターのemotions(+emotions_baseline)、goals、knowledge、secrets、private_mind、speech、statusと、そのキャラクター起点の関係(`relationships`のうち`from_`が本人のもの)
2. `GET /api/project/{name}/gm/world` — world summary/parameters、threats(id/name/pressure/stages+次の未超過閾値)、pacing設定、scenes(id/status/location/mood/summary/hidden_facts/reader_visible_facts)
3. `GET /api/project/{name}/gm/timeline?from=N&limit=M` — timelineエントリを`events.yaml`からハイドレートして返す(`agents.event_history.load_recent_events`は「直近N *ターン*」専用で`from`/`limit`ページングに向かないため、同等の読み取りループをservice層に実装)
4. `GET /api/project/{name}/gm/threads` — `unresolved_threads`(notes/opened_turn含む全フィールド+派生の`related_event_count`)+`memory_summaries`
5. `GET /api/project/{name}/gm/turn/{n}` — そのターンの`rolls.yaml`/`checks.yaml`/`state_diff.yaml`をそのまま返す。ターンディレクトリが無ければ404

**UI**(`web/page.py`):

6. 「GMビュー」トグルボタン+パネル: キャラクターカード(emotion値+baseline注記)、脅威pressure表示(次の閾値付き)、シーン一覧(hidden_facts含む)、未解決スレッド一覧、visibilityバッジ付きタイムライン、ターン番号入力→詳細取得

**制約**: 020/021-022/023と同じ — `src/living_narrative/web/**`・`tests/web/**`のみ、コア改変禁止、127.0.0.1固定。今回は並行して別ワーカーがコアエンジンファイルを変更しているため、コア(`pipeline/`, `agents/`, `state/`等)は一切触れない。

## 完了条件

- [x] `gm/characters`がsecrets/private_mind/knowledge/relationshipsを含む(既存`/status`は含まないまま)
- [x] `gm/world`が脅威の次の未超過閾値・pacing・シーンのhidden_factsを返す
- [x] `gm/timeline`が`from`/`limit`でページングでき、各イベントにvisibilityが付く
- [x] `gm/threads`がnotes/opened_turn/related_event_count/memory_summariesを返す
- [x] `gm/turn/{n}`がrolls/checks/state_diffを返し、存在しないターンは404
- [x] 回帰: `/status`・`/narration`・`/turns`がsecrets/private_mind/hidden_facts文字列を含まないまま(漏洩境界維持)
- [x] UIにGMビュートグル・キャラクターカード・脅威表示・シーン/スレッド一覧・visibilityバッジ付きタイムライン・ターン詳細取得がある
- [x] 既存568+テスト回帰なし、ruffクリーン

## 関連ファイル

- 変更: `src/living_narrative/web/{app,service,page}.py`、新規テスト `tests/web/test_gm_api.py`
- 参照のみ: `state/models.py`(CharacterState/ThreatTrack/UnresolvedThread等)、`state/store.py`(StateStore.load)、`agents/event_history.py`(load_recent_eventsとの使い分けの根拠)
- DAG: `docs/plan/feature-dag.md`
