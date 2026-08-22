---
id: 135
title: 著者レビュー前の本文量・物語進行 Quality Gate
status: in-progress
created: 2026-08-23
type: quality-gate
priority: P0
parent: 088
blocked_by: []
labels: [narration, quality, author-review, privacy, v1.0.0]
---

# 135: 著者レビュー前の本文量・物語進行 Quality Gate

## 背景

v1.0.0 RCの実LLM runで、turn 1–6の本文が673–888文字、turn 7が476文字だった。turn 7は著者レビューで「物語が進んでいる気配がない」「極めて短い」としてreviseされた。既存ADR-0010の機械SLOはstall・thread・leak・game機能を扱うが、各turnの本文量と著者が読む前の局所的な進行品質を検出しない。

> 本Issueは本文の長さだけで商業品質を判定しない。短すぎる候補と連続した進行不足を、著者が明示的にaccept/reviseする前に止め、判断材料をreader-safeに提示する。

## 決定

新しいproject-level `narrative_quality`設定を**default disabled**で追加する。Book Stateのschema migrationは行わない。設定が有効なときだけ、既存Check→Commit境界に`narrative_quality` checkerを登録する。

| 設定 | RC推奨値 | 意味 |
|---|---:|---|
| `minimum_narration_characters` | 1,200 | frontmatterを除く日本語本文がこれ未満なら`error` findingで`stopped_for_review`にする。 |
| `maximum_consecutive_stall_turns` | 2 | 進行eventがない状態がこの閾値を超えたら`error` findingで停止する。 |
| `target_narration_characters` | 1,600 | LLM narratorへの目標値。hard maxではなく、可視情報を捏造せずに描写・反応・因果を充実させる指針とする。 |

進行eventは既存の`is_advancement_event`により定義される新scene・脅威stage・物語上の明示的進展である。checkerは本文、reader-visible resolved event、既存reader-visible contextのみを読み、prompt、GM/private context、credential、absolute pathをfindingやCLI/web outputへ出さない。

LLM narrator promptは、target値を満たすよう「可視情報に基づくbefore/afterの因果」「行動・知覚・反応・場面変化」を書くことを求める。ただし、情報不足を理由に新しい事実・内心・隠し設定を創作してはならない。

## 完了条件

- [x] `narrative_quality`はdefault disabledで既存project.yamlと後方互換を保つ。
- [x] opt-in時、short narrationは固定のreader-safe findingで`stopped_for_review`となり、auto-applyしない。
- [x] opt-in時、許容値を超える連続stallは固定のreader-safe findingで停止する。
- [x] LLM narrator promptにtarget lengthと可視情報だけで因果的進展を描く指針を追加する。
- [x] author reviewのaccept/reviseを自動実行しない。
- [x] mock/LLM narrator/pipeline/CLI・web reviewのfocused回帰、全回帰、lint、format、diff checkを通す。
- [ ] RC gateは新規run IDで再実行し、著者が本文を明示accept/reviseする。旧runのturn 7を自動修復しない。

## 実装記録

`narrative_quality` は `enabled: false` を既定とし、RC推奨値として
`minimum_narration_characters: 1200`、`maximum_consecutive_stall_turns: 2`、
`target_narration_characters: 1600` を持つ。targetがminimum未満の矛盾した設定は
読込時に拒否する。enabled時だけnarrator payloadの `narration_target_characters` を設定し、
LLMには可視情報のみを根拠とするbefore/afterの因果、行動・知覚・反応・場面変化を求める。

checkerの公開findingは `narration_too_short` または
`consecutive_stall_limit_exceeded` の固定コードだけであり、候補本文、prompt、GM/private context、
credential、absolute pathを含めない。error findingは既存Check→Commit境界により
`stopped_for_review` とnon-applied StateDiffに変換され、著者のaccept/reviseを自動実行しない。

## 非対象

- 文字数だけでの商業品質判定、LLMによる自己評価だけでのaccept、Book State migration。
- 旧RC runのstateを修復して再開すること。品質gate変更後は新しいrun IDを用いる。

## 関連ファイル

- `src/living_narrative/narration/llm_narrator.py`
- `src/living_narrative/safety/pacing_check.py`
- `src/living_narrative/safety/registry.py`
- `src/living_narrative/pipeline/driver.py`
- `src/living_narrative/state/models.py`
- `docs/adr/0010-quality-gate-narrative-slo.md`
- `docs/real-llm-benchmark.md`
