---
id: 033
title: 構造化inventory runtime
status: in_progress
created: 2026-07-11
---

# 033: 構造化inventory runtime

## 背景

`CharacterState.inventory` は文字列配列のため数量や同一アイテムを安全に追跡できず、取得・使用・喪失もターンの `StateDiff` に落とせない。D-2/D105のPydantic正本とD107のdiff-only mutationを守りながら、既存projectをschema version 1のまま読める構造化inventoryへ移行する。

## 設計

1. `InventoryItem` を `id` / `name` / `qty`（必要なら `note`）の明示モデルとして追加し、`CharacterState.inventory` を正規の構造化配列にする。qtyは正整数を境界で検証する。
2. list-level `BeforeValidator` で旧 `str` 要素を順序どおり `item_001`, `item_002`, ...、qty=1へ決定的に強制変換する。同名・日本語slug衝突を避けるためname由来IDは使わず、idをoptionalにしない。schema versionは1のままとする。
3. character agent出力へdefault空の `inventory_updates`（gain/use/lose）を追加し、所持品が実際に増減したときだけ出力するprompt節を追加する。
4. state managerは更新を必ず `StateDiff(target=character, path=inventory...)` へ変換する。gainの新規IDは当該inventoryの最大番号+1、未知itemのuse/lose、非正qty、在庫超過はreject理由付きで拒否し、直接mutationしない。
5. mist_stationテンプレートを新形式へ更新し、新モデルをschema exportへ登録する。

## 完了条件

- [ ] `InventoryItem(id/name/qty)` がPydantic v2の正モデルで、qty境界を検証する
- [ ] 旧 `list[str]` を決定的な `item_NNN`・qty=1へ読み替え、schema version 1の後方互換を保つ
- [ ] character agent出力/promptにdefault空のinventory更新がある
- [ ] gain/use/loseがStateDiffとして適用され、直接mutationしない
- [ ] 未知item、負/ゼロqty、在庫超過を理由付きで拒否する
- [ ] mist_stationとschema exportが新形式に対応する
- [ ] 全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/state/models.py`
- `src/living_narrative/state/schema_export.py`
- `src/living_narrative/agents/models.py`
- `src/living_narrative/agents/character.py`
- `src/living_narrative/agents/state_manager.py`
- `src/living_narrative/templates/mist_station/state/characters/*.yaml`
- `tests/agents/`, `tests/test_state_model.py`, `tests/templates/`
