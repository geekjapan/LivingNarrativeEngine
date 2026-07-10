---
id: 039
title: visual profileスキーマ
status: done
created: 2026-07-11
---

# 039: visual profileスキーマ

## 背景

E8の画像プロンプト生成・VN rendererでは、キャラクターの外見、背景、画風をターンをまたいで一貫させる正規データが必要になる。Issue 040以降のruntime消費に先立ち、Pydantic v2を単一正本とするoptionalなvisual profileを定義し、保存・読込・schema export・最小限のGM表示まで通す。

## 設計

1. キャラクター外見を表す `CharacterVisualProfile`、背景を表すprofile、画風固定パラメータを表すprofileを、extraへ逃げない明示的なPydanticモデルとして追加する。
2. project stateからvisual profile一式をoptionalにloadできるよう `StateStore` を拡張し、既存projectにファイルがなくても後方互換で読み込めるようにする。
3. 新規モデルを `SCHEMA_MODELS` に登録し、mist_stationテンプレートへ実値1式を追加する。
4. 定義だけで終わらせず、web GM characters paneへ外見profileの要約を1行表示する。ユーザー由来文字列は必ず `escapeHtml` する。画像prompt生成・provider呼出しはIssue 040以降の責務とする。

## 完了条件

- [x] character/background/style-lockのPydanticモデルが明示的な正フィールドで定義される
- [x] visual profileファイルのoptional loadがあり、欠落時も既存projectを読める
- [x] 新規モデルのJSON Schemaがexportされる
- [x] mist_stationテンプレートにschema-validな実値1式がある
- [x] web GM characters paneにescapedなvisual profile要約が1行表示される
- [x] 画像生成などのruntime消費を先取りせず、全テスト・ruff check・ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/state/models.py`
- `src/living_narrative/state/schema_export.py`
- `src/living_narrative/state/store.py`
- `src/living_narrative/templates/mist_station/state/`
- `src/living_narrative/web/service.py`
- `src/living_narrative/web/page.py`
- `tests/test_state_model.py`, `tests/templates/`, `tests/web/`
