---
id: 013
title: 関係性が不変(diff機構は完備だがagent出力からの更新経路が無い)
status: done
created: 2026-07-07
---

# 013: 関係性ダイナミクス(relationship_updates)

## 背景

`RelationshipState`(trust/affection/tension/suspicion、composite key `<from>__<to>`、D116)はキャラ文脈に供給され(context_builder:51)、diff機構も relationship target・delta clamp・テストまで完備。しかし **CharacterAgentOutput に関係性フィールドが無く、state_manager にも変換経路が無い** — 感情(Issue 006/010以前)と同じ「定義のみ・消費ゼロ」パターン。20ターン走ってもリナとカイの関係値は初期値のまま。

## 設計

Issue 006のemotion_deltasと同型:

1. `RelationshipUpdateCandidate(to: CharacterId, dimension: Literal["trust","affection","tension","suspicion"], delta: int)` を `CharacterAgentOutput.relationship_updates: list[...] = []`(**default空** — 必須にしない。mockが乱数で埋める問題を回避、後方互換)
2. state_manager `_character_output_changes` 拡張: actor→`to` の関係を `target="relationship", id=f"{actor}__{to}", op="delta", path=dimension` に変換(既存clamp経由)。visibility=character。ガード: 関係ペアが存在しない/to==self/未知dimension は reject(理由付き)
3. プロンプトv5: 「## 関係の更新」— 出来事で相手への見方が動いたときだけ、-15〜+15、対象は scoped_state.relationships にいる相手のみ
4. 更新は「自分から相手への見方」のみ(from=actor固定)。相手側の対称更新はしない(非対称が正)

## 完了条件

- [x] スキーマ+state_manager変換+ガード(reject理由付き)
- [x] プロンプトv5に関係更新指針
- [x] mock全テストpass(既存469+ → 476)
- [x] 実LLM 8ターン(`sandbox/issue013_llm`): 4/8ターンでrelationship delta(リナ→カイ tension+2/suspicion+3/trust+2/suspicion+3、非対称・-15〜+15内)、最終relationships.yamlに反映(trust 80→82等)。rejectガードは実LLMでは未発火(unit test済み)

## 関連ファイル

- `src/living_narrative/agents/models.py:58`(CharacterAgentOutput)
- `src/living_narrative/agents/state_manager.py:198`(_character_output_changes)
- `src/living_narrative/state/diff.py:214`(relationship target既存)/ `state/models.py:264`(RelationshipState)
- `src/living_narrative/agents/character.py`(PROMPT_TEXT v5)
- `src/living_narrative/templates/mist_station/state/relationships.yaml`(5有向ペア既存)
