---
id: 037
title: Resolveスロットによる簡易戦闘
status: done
created: 2026-07-11
---

# 037: Resolveスロットによる簡易戦闘

## 背景

Issue 032でstats/skillsを用いた判定は実行できるが、攻撃者・防御者・stakesを持つ交戦を既存のResolve契約へ載せ、HP消耗と重大失敗を監査可能に扱う経路がない。D-3に従い8フェーズを変えず、既存Conflict Resolverのroll/event/effectsを拡張して最小の戦闘帰結を表現する。

## 設計

1. `ActionCandidate.effects`内のcombat payloadをPydantic v2境界で検証する。attacker、defender、stakes、判定に使うstat/skill/target、成功時damage、任意の`life_or_death`を明示し、未知character、自己攻撃、非正damage、欠落能力値を理由付きで拒否する。
2. combat candidateは既存Resolveスロット内でIssue 032と同じstats/skills modifierと`RandomEngine.roll_chance`を使い、1交戦につき1rollで成功/失敗を決める。新しいpipeline phaseやラウンド制は追加しない。
3. rollは既存`record_roll`で`rolls.yaml`へ保存し、combat eventの`roll_ids`へD121準拠で関連付ける。結果、attacker/defender/stakes、damage、成否をevent effectsへ保持する。
4. HPは`CharacterState.stats.hp`を正本とし、damage/消耗はState Managerが`StateDiff(target=character, op=delta, path=stats.hp)`へ変換する。既存clampを使い、直接mutationしない。
5. 戦死級の失敗はroll severityをcriticalにし、`life_or_death`と`heavy_roll_failure`停止条件を通じてGM reviewへ送る。即時の`status=dead`変更は行わない。
6. 既存のexclusive conflict順序、非combat candidate、RNG再現性、roll抽出、stop conditionを壊さない。

## 非目標

- ラウンド制、initiative、位置取り、射程、装備補正マトリクス、複数対象攻撃
- 新pipeline phase、新しいHP専用state field、即死の自動確定

## 完了条件

- [x] combat payloadを境界で検証し、attacker/defender/stakesを保持する
- [x] 既存Resolveスロット内だけでstats/skills判定を再利用する
- [x] 1交戦のrollが`rolls.yaml`とevent `roll_ids`へ記録される
- [x] damageが`stats.hp`へのclamp付き`StateDiff(op=delta)`になる
- [x] `life_or_death`重大失敗がGM review用stop conditionへ連動し、即死させない
- [x] 非combat Resolve、決定性、未知character/能力値、不正damageを回帰テストする
- [x] 新pipeline phaseと直接state mutationがない
- [x] 全テスト、ruff check、ruff format checkがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 検証結果

- 実装コミット: `870fe695110d50a260b1cc172ea30b4089690e36`
- Wave 7統合後: `NO_COLOR=1 uv run pytest` 922件pass
- `uv run ruff check .`、`uv run ruff format --check .` pass

## 関連ファイル

- `src/living_narrative/agents/conflict_resolver.py`
- `src/living_narrative/agents/models.py`
- `src/living_narrative/agents/state_manager.py`
- `src/living_narrative/random/engine.py`
- `src/living_narrative/session/stop_conditions.py`
- `tests/agents/test_conflict_resolver.py`
- `tests/agents/test_state_manager.py`
- `tests/pipeline/`
- `tests/session/test_stop_conditions.py`
