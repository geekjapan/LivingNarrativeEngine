---
id: 042
title: VNレンダラとVN台本export
status: done
created: 2026-07-11
---

# 042: VNレンダラとVN台本export

## 背景

物語turnをビジュアルノベル制作へ渡せる構造化台本がない。既存のnarration rendererとsession再構築を拡張し、readerに見えてよいナレーター出力だけから、会話・地の文・立ち絵・背景・音響指示を再利用可能な形で書き出す。

## 設計

1. `RendererRegistry`の既存renderer挙動とdefaultを変えず、`vn`を追加登録する。影響分析はCRITICALのため、変更は登録追加と独立renderer実装に限定する。
2. turn narrationを、話者ラベル付き台詞、地の文、`visual_profiles`のcharacter idを参照する立ち絵指定、背景指定、BGM/SFXコメントへ決定論的に整形する。
3. session全体を再構築し、`exports/`配下へ`script.yaml`と`script.md`を生成するexporterとCLI subcommandを追加する。
4. 入力はreader可視のnarrator出力だけに限定し、`gm_vault`やGM専用stateを参照しない。必要なLLM整形は決定論的抽出から分離し、既存novel exporterと同じ`LLMGateway`/profile bindingを使う。
5. renderer登録、台本構造、CLI出力、情報スコープをテストする。

## 完了条件

- [x] `vn` rendererが登録され、既存rendererの挙動とdefaultが不変
- [x] 台詞、地の文、立ち絵、背景、BGM/SFX指示を表現できる
- [x] session全体を`script.yaml`と`script.md`へexportできる
- [x] CLI subcommandからprofile bindingを選択できる（LLM使用時）
- [x] reader可視のnarrator出力だけを入力とし、GM専用情報を参照しない
- [x] 決定論的構造抽出とLLM整形が分離されている
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 検証記録

- 2026-07-11: 034統合済みmainで`NO_COLOR=1 uv run pytest` 829件、
  `uv run ruff check .`、`uv run ruff format --check .`がpass。
- 2026-07-11: canonical turn採用、reader-only入力境界、LLM構造化、
  visual profile ID allowlist、未知参照warningを二軸レビューで確認。

## 関連ファイル

- `src/living_narrative/narration/renderers.py`
- `src/living_narrative/export_replay/`
- `src/living_narrative/cli/export.py`
- `src/living_narrative/state/models.py`
- `tests/narration/`
- `tests/export_replay/`
- `tests/cli/`
