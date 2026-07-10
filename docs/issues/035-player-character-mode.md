---
id: 035
title: player_character参加モード配線
status: done
created: 2026-07-11
---

# 035: player_character参加モード配線

## 背景

`UserMode.PLAYER_CHARACTER`と`ProjectConfig.player_char_id`、モード別permissionは存在するが、PC本人のユーザー入力をAct/Resolveへ渡す標準経路がない。現状のstatus/web表示もPC視点の情報境界を一貫して保証していないため、既存InterveneとActionCandidateを使ってPC参加をturnフローへ接続する。

## 設計

1. `living-narrative turn --pc-action <text>`を追加する。projectが`player_character`で有効な`player_char_id`を持つ場合だけ受理し、当該characterをtargetとする既存`character_directive` interventionとして保存する。
2. Act slotはPC本人についてLLM生成candidateを使わず、確定済みPC directiveをそのcharacterの`ActionCandidate`相当へ変換する。他characterのcandidateと同じResolveへ渡し、exclusive conflictや判定を迂回しない。
3. `MODE_PERMISSIONS`を既存intervention型の範囲で拡張し、PC本人への`character_directive`、本人のcharacter checkとしての`dice_roll_request`、`stop_condition`だけを許可する。所持品使用は本人向けdirectiveの検証済みconstraintsをIssue 033の`inventory use`候補へ変換し、State Managerの既存use/reject経路へ渡す。新intervention型は追加しない。
4. targetは常に`player_char_id`へ固定し、他character、world、gm_vault/canon編集、readerへの強制公開を拒否する。`can_view_gm_vault=False`を維持する。
5. CLI statusとweb表示はplayer_characterモードで、自キャラのstate/knowledge/private_mind、自キャラが知る可視情報、reader/scene可視情報だけを返す。他characterのprivate_mind/secrets、GM Vault、未知hidden factsを含めない。ユーザー由来文字列をHTMLへ出す場合は`escapeHtml`を必須とする。
6. PCがdead/missingの場合は入力を通常適用せず、既存stop/review契約へ送る。pipeline phaseは増やさず、artifactとpermission rejectionを監査可能に残す。

## 完了条件

- [x] `turn --pc-action`がbound PCの既存interventionとして保存される
- [x] PC入力がPCのActionCandidate相当として他candidateと同じResolveへ入る
- [x] PC本人のcharacter checkが`dice_roll_request`からIssue 032経路へ入る
- [x] PC本人のinventory useがIssue 033の既存StateDiff/reject経路へ入る
- [x] permission matrixが本人targetだけを許し、GM系介入を拒否する
- [x] status/webがPC視点へ絞られ、gm_vault・他者秘密・未知hidden factsを漏らさない
- [x] dead/missing PCがGM review用stop conditionへ送られる
- [x] pipeline phase追加と直接state mutationがない
- [x] CLI/pipeline/session/webの回帰を含む全テストとruffがpassする
- [x] 無関係変更がなく、GitNexus `detect_changes`で影響範囲を確認している

## 検証結果

- 実装コミット: `097e56470b9164e4f66ef90d370fcea66999e456`
- Issue 037上へ競合なしでrebaseし、Wave 7統合後に`NO_COLOR=1 uv run pytest` 922件pass
- `uv run ruff check .`、`uv run ruff format --check .` pass

## 関連ファイル

- `src/living_narrative/cli/turn.py`
- `src/living_narrative/session/mode.py`
- `src/living_narrative/pipeline/driver.py`
- `src/living_narrative/pipeline/builtin_slots.py`
- `src/living_narrative/agents/character.py`
- `src/living_narrative/agents/state_manager.py`
- `src/living_narrative/intervention/`
- `src/living_narrative/cli/status.py`
- `src/living_narrative/web/`
- `tests/cli/`, `tests/pipeline/`, `tests/session/`, `tests/web/`
