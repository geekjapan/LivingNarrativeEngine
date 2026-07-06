---
id: 027
title: chapter outline + novel draft exporter(026の構造から章立て→小説風Markdown)
status: done
created: 2026-07-07
---

# 027: chapter outline + novel draft exporter

## 背景

DAG Track C。Phase 6「ログから章原案を作れる」「小説風Markdownを出力できる」。026のSessionReconstruction(シーン・key_events・転換点)が構造を提供済み。既存narrationは各ターン独立の断章なので、繋げただけでは反復・継ぎ目が残る(replay.mdの現状)。章立て+整形パスで「読める初稿」に上げる。

## 設計

1. **chapter outline(決定論)**: `export_replay/outline.py` — SessionReconstructionから章構成を導出。章境界 = シーン遷移 + 転換点(stage発火)で分割(1章=1シーン基本、長いシーンは転換点で分割、目安3〜8ターン/章)。各章: タイトル候補(シーンlocation+転換点から機械生成)、ターン範囲、含まれるkey_events、その章のnarration本文(reader可視)
2. **novel draft(LLM整形)**: 章ごとに1 LLM呼び出し — 入力: 章のnarration連結+前章までのあらすじ(逐次)+章のkey_events。指示: 反復除去・継ぎ目の平滑化・視点/時制統一、**新規事実の発明禁止**(素材にある内容のみ)。narrator用プロンプトとは別の推敲プロンプト(export時のみ、パイプライン外)
3. CLI: `living-narrative export outline --project P`(outline.yaml+outline.md、LLM不要)/ `living-narrative export novel --project P [--profile prose]`(novel_draft.md。LLM必須、プロジェクトのllm設定を再利用)
4. リーク安全: 素材はreader可視のみ(replay/026 reader版と同じゲート)→ 構造的にリーク不能
5. LLM失敗時: 章単位でリトライ、最終失敗章は元narration連結にフォールバックして続行(全体を落とさない)

## 完了条件

- [x] outline: mock遷移プロジェクトで章分割・タイトル・ターン範囲が妥当(決定論テスト)
- [x] novel: mock LLMで章数分の呼び出しが走り、novel_draft.mdが章立てで出る(内容はmockなので構造のみ検証)。失敗章フォールバックのテスト
- [x] reader可視ゲートのテスト(gm_only素材が入力payloadに混入しない)
- [x] mock全テストpass(631+)
- [x] 実データ確認: bench20_llmで5章構成のnovel_draft.md生成(全章LLM整形、フォールバックゼロ)。通読評価=初稿合格ライン: 継ぎ目消滅、カイの秘密が性格描写として機能、捏造・リークなし。発見バグ(遷移ターンの章二重収録→第5章冒頭が第4章末尾を再演)は修正済み(outline章範囲のターン分割保証+テスト2件)

## 関連ファイル

- `src/living_narrative/export_replay/`(reconstruction.py基盤、新規outline.py/novel.py)
- `src/living_narrative/cli/export.py` / `pipeline/llm_gateway.py`(LLM呼び出し再利用)
- DAG: `docs/plan/feature-dag.md`
