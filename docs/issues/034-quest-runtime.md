---
id: 034
title: クエスト台帳ランタイム
status: done
created: 2026-07-11
---

# 034: クエスト台帳ランタイム

## 背景

キャラクターの明示的な目標と達成条件を継続的に追跡する正規台帳がない。既存の未解決スレッド台帳を手本に、クエストを状態・エージェント出力・文脈供給まで一貫して扱えるようにする。スレッドは物語の糸や伏線を追跡し、クエストは明示的な目標と達成条件を追跡するものとして役割を分ける。

## 設計

1. `quest_NNN`形式のid、title、`open | advanced | resolved | failed`のstatus、objectives、related_event_idsを持つPydantic v2 `Quest`モデルを追加する。
2. `quests.yaml`を任意状態ファイルとして読み書きし、ファイルがない既存projectは空コレクションとして扱う。schema exportとmist_stationにも実値1件を追加する。
3. character/narrator出力にdefault空の`quest_updates`を追加し、open/advance/resolveを`StateDiff`へ変換する。未知quest、不正遷移、不正idは理由付きrejectとし、状態を直接mutationしない。
   reader可視questのopenはnarratorのみとし、characterの私的目標は`CharacterState.goals`で扱う。GM介入によるopenはE7/038で検討する。
4. 未完了questを、既存open threadと同様にcharacter/narratorのreader-safe文脈へ供給する。GM専用情報は混入させない。
5. Questの遷移、永続化、文脈供給、拒否経路を回帰テストで固定する。

## 完了条件

- [x] `Quest`モデルと`quests.yaml`のoptional load/save経路がある
- [x] character/narratorの`quest_updates`がdefault空で後方互換を保つ
- [x] open/advance/resolveが`StateDiff`経由で適用される
- [x] 未知questと不正遷移が理由付きでrejectされる
- [x] 未完了questがcharacter/narrator文脈にreader-safeに供給される
- [x] schema exportとmist_stationにquest実値がある
- [x] threadとquestの役割分担が文書化されている
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 検証記録

- 2026-07-11: main統合後に`NO_COLOR=1 uv run pytest` 818件、
  `uv run ruff check .`、`uv run ruff format --check .`がpass。
- 2026-07-11: reader可視questのopenをnarratorに限定し、character更新の型境界、
  reader eventだけの関連付け、GitNexus影響範囲を再レビュー。

## 関連ファイル

- `src/living_narrative/state/models.py`
- `src/living_narrative/state/store.py`
- `src/living_narrative/state/schema_export.py`
- `src/living_narrative/agents/models.py`
- `src/living_narrative/agents/state_manager.py`
- `src/living_narrative/agents/context.py`
- `src/living_narrative/narration/context.py`
- `src/living_narrative/narration/models.py`
- `src/living_narrative/narration/llm_narrator.py`
- `src/living_narrative/templates/mist_station/`
- `tests/`
