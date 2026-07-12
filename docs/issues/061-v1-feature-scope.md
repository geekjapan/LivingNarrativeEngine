---
id: 061
title: 1.0に含める機能とpost-1.0拡張を決定する
status: open
created: 2026-07-12
type: wayfinder:grilling
priority: P1
parent: 052
blocked_by: [053, 057, 058, 059, 060]
---

# 061: 1.0に含める機能とpost-1.0拡張を決定する

## 問い

既存1.0体験を成立させるために、3つ目のsample、実画像/TTS、gallery、Web review拡張、map/NPC/reward、実migration等のどれを1.0へ含め、どれを明示的にpost-1.0へ送るか。

## 背景

現行は`mist_station`と`orbital_echo`の2実用sampleで、`minimal`は空workspaceである。Phase 8は実provider／gallery／本文画像表示を企画したが、Issue 041/043はprovider境界＋mockへ意図的に縮小した。Phase 7のmap/location graph、NPC AI、reward systemも未実装だが、コアTRPG受入条件は通過している。

## 解決条件

- primary journeyへ直接効くものだけを1.0候補にする
- 各候補の価値、依存、security/cost、保守負担を比較する
- `project_plan`の元スコープからの再定義を明記する
- post-1.0 backlogを順序なしの願望集ではなく、目的別epicへまとめる
- scope決定がRelease契約と矛盾しないことを確認する

## 関連ファイル

- `docs/project_plan.md`
- `docs/issues/031-stats-skills-schema.md`
- `docs/issues/041-image-provider-cache.md`
- `docs/issues/043-voice-tts-export.md`
- `docs/issues/044-schema-version-migrations.md`
- `src/living_narrative/templates/`

