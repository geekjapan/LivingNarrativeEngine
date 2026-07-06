---
id: 001
title: キャラクターエージェントのシステムプロンプト書き直し(日本語必須・ペルソナ注入・visibility規則)
status: open
created: 2026-07-06
---

# 001: キャラクタープロンプト書き直し

## 背景

ターン1実走(mist_run_001)で `agents/character.py` の `PROMPT_TEXT` が英語1文(~25トークン)しかないことが判明。3143プロンプトトークンのほぼ全てがスコープ済みコンテキストJSONで、指示が皆無に近い。結果:

- char_002 が全編英語で行動出力(D106「物語コンテンツは日本語第一」違反)
- 内心の生ダンプ(整形されない思考の羅列)

deep-reasoner診断で「最もレバレッジの高い修正」と認定(所見#2)。

## 完了条件

- [ ] `PROMPT_TEXT` を書き直す: 全 `content` の日本語出力を必須化(D106)、スコープ済みstateからペルソナ/口調を注入、出力形式を明示、visibilityタグ付け規則を記載
- [ ] 任意: パース後に `content` がかな/漢字を含むことのassert
- [ ] mist_run_001 で新ターンを実走し、全キャラが日本語で出力することを確認
- [ ] 既存テスト green(`uv run pytest`)

## 関連ファイル

- `src/living_narrative/agents/character.py:15-18`(PROMPT_TEXT)
- 関連Issue: [002](002-inner-reaction-visibility-clamp.md)(visibility規則はプロンプトとコード両面で守る)
