---
id: 031
title: stats/skills スキーマとキャラクターシート表示
status: in_progress
created: 2026-07-11
---

# 031: stats/skills スキーマとキャラクターシート表示

## 背景

E7のゲーム拡張では能力値と技能が判定・戦闘・所持品の共通基盤になるが、現在の `CharacterState` には正規フィールドがない。D-2/D105に従い、Pydantic v2スキーマへ明示的に追加し、次のruntime issueに先立って保存・読込・閲覧できる状態を作る。

## 設計

1. `CharacterState` に `stats: dict[str, int]` と `skills: dict[str, int]` をdefault空の正フィールドとして追加する。`extra=allow` による暗黙保持には頼らない。
2. 新しいPydantic modelは作らないため `state/schema_export.py` の `SCHEMA_MODELS` 構成は変えず、既存 `CharacterState` のJSON Schema出力へ両フィールドが現れることをテストする。
3. mist_stationの全キャラクターへ物語設定に沿う実値を設定し、templateのload/init経路を通して検証する。
4. `living-narrative status` の人間可読/JSON character sheetと、web GM characters API/paneへstats/skillsをread-only表示する。更新経路・判定ルールはIssue 032/033以降の責務とする。

## 完了条件

- [ ] `CharacterState.stats` / `skills` が `dict[str, int]`・default空の正フィールドである
- [ ] schema exportに両フィールドが現れ、既存データは後方互換でloadできる
- [ ] mist_station全キャラクターにstats/skillsの実値がある
- [ ] status CLIの人間可読/JSON出力にキャラクターシートが表示される
- [ ] web GM characters API/paneにstats/skillsが表示される
- [ ] runtime mutation経路を追加せず、全テスト・ruff check・ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/state/models.py` (`CharacterState`)
- `src/living_narrative/state/schema_export.py` (`CharacterState` schema export、構成変更なし)
- `src/living_narrative/templates/mist_station/state/characters/*.yaml`
- `src/living_narrative/cli/status.py`
- `src/living_narrative/web/service.py` (`get_gm_characters`)
- `src/living_narrative/web/page.py` (`renderGmCharacters`)
- `tests/test_state_model.py`, `tests/templates/`, `tests/cli/`, `tests/web/`
