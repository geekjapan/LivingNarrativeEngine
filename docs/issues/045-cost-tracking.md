---
id: 045
title: LLM cost tracking
status: in_progress
created: 2026-07-11
---

# 045: LLM cost tracking

## 背景

各LLM呼び出しの `CallMetadata` と、ターンごとの `meta.yaml` にある `llm_tokens_total` / `llm_calls` は既に記録されているが、プロジェクト全体の利用量と概算費用を確認する導線がない。新しい計測経路は増やさず、既存メタデータを集計してCLIとwebのGM paneから把握できるようにする(D-6)。

## 設計

1. 正規の `turn_NNNN/meta.yaml` を読み、LLM呼び出し回数、prompt/completion/total token、モデル別内訳を集計する。discarded/rolledback/壊れたメタデータの扱いを既存run規約に合わせ、テストで固定する。
2. モデル別価格テーブルをコード上の単一箇所に置き、入力・出力token単価から概算費用を算出する。未知モデルは誤った金額を補完せず、利用量を保持したまま価格不明として扱う。
3. `living-narrative status` に簡潔な利用量・概算費用を表示し、既存のstatus情報を壊さない。
4. webのstatus API/GM paneにも同じ集計結果を表示し、CLIとwebで計算ロジックを共有する。

## 完了条件

- [ ] `meta.yaml` の `llm_tokens_total` / `llm_calls` からproject全体・モデル別のcall/token集計が得られる
- [ ] モデル別価格テーブルとprompt/completion token別の概算費用計算があり、未知モデルを安全に扱う
- [ ] status CLIに集計が表示される
- [ ] web status APIとGM paneに同じ集計が表示される
- [ ] 欠落・不正・discarded/rolledback metaを含む境界ケースのテストがある
- [ ] 既存テストを含む全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係なファイル変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/llm/metadata.py` (`CallMetadata`, `build_turn_meta`)
- `src/living_narrative/pipeline/writer.py` (`build_meta_dict`)
- `src/living_narrative/cli/status.py`
- `src/living_narrative/web/service.py` (`get_status`)
- `src/living_narrative/web/app.py` (status API)
- `src/living_narrative/web/static/` (GM pane表示)
- `tests/llm/`, `tests/cli/`, `tests/web/`
