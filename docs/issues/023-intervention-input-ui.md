---
id: 023
title: Web UI — Intervention Input(構造化介入フォーム+自由文)
status: done
created: 2026-07-07
---

# 023: Intervention Input(Track B、021/022の続き)

## 背景

DAG Track B。CLIでは `turn --intervene`(自由文)/ intervention drafts で介入できるが、UIに介入手段が無い。Phase 4の中核価値=「GMコックピット」の入口。

## 設計

**API**(`web/service.py` / `app.py`):

1. `POST /api/project/{name}/turn` 拡張 — body `{"free_text": str | null, "drafts": [intervention dict] | null}` を受けて `TurnPipeline.run(project_path, intervention_text=..., intervention_drafts=...)` に渡す(既存パラメータ、再実装しない)。auto実行中は409
2. `GET /api/project/{name}/interventions` — `interventions.yaml` 履歴 + 直近ターンの `intervention.yaml`(採用/rejection、rejection理由込み)
3. `GET /api/project/{name}/permissions` — project.yaml の user_mode と、そのmodeで許可される介入型一覧(session/mode.py の permission table を参照。D114: 真実の源はsession-autonomy)

**UI**(`web/page.py`):

4. 介入パネル: 自由文テキストエリア+「介入して次ターン」ボタン、構造化フォーム(型select — permissionsで許可される型のみ表示、target/content/visibility入力)、直近介入の採用/棄却結果表示(棄却理由付き)

**制約**: 021/022と同じ — web/とtests/のみ、コア改変禁止、127.0.0.1固定。

## 完了条件

- [x] free_text付きturnがintervene相を通る(httpxテスト: intervention.yamlに記録される)
- [x] drafts付きturnで許可介入が適用され、無権限介入はrejections入り(watcher/full_gmの両モードでテスト)
- [x] permissions APIがuser_mode別の許可型を返す
- [x] interventions履歴APIが動く
- [x] UIから自由文介入→次ターン実行が可能(手動smoke)
- [x] 既存536+テスト回帰なし、ruffクリーン

## 関連ファイル

- 変更: `src/living_narrative/web/{app,service,page}.py`、新規テスト `tests/web/test_intervention_api.py`
- 参照のみ: `pipeline/driver.py`(runのintervention引数)、`session/mode.py`(permission table)、`intervention/`
- DAG: `docs/plan/feature-dag.md`
