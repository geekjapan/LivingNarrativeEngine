---
id: 061
title: 1.0に含める機能とpost-1.0拡張を決定する
status: done
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


## 決定(2026-07-13承認済)

方針: **1.0へ新機能は追加しない**。1.0 scope=既存機能+054-060で確定したmust修正のみ。各候補のD3判定:

| 候補 | 判定 | 根拠 |
|---|---|---|
| 3つ目の実用sample | **post-1.0** | 実用2つ(mist_station/orbital_echo)でpersona評価に十分(058調査)。D1完走に不要 |
| 実画像/TTS provider | **post-1.0** | ADR-0005 D3が派生レイヤと明記。provider境界+mockは041/043で出荷済 |
| gallery/本文画像表示 | **post-1.0** | 同上(Phase 8派生レイヤ) |
| Web review拡張(edit/rerun_turn Web化) | **should(1.1)** | CLI手動回避あり・互換非破壊・後付け可(D3 should定義そのもの) |
| map/location graph・NPC AI・reward | **post-1.0** | Phase 7未実装だがコアTRPG受入通過済。D1正常系に不要 |
| 実migration | **1.0 must(既定)** | βschema凍結+migration regression harnessは055/059のmustに含まれる。登録migration自体はschema変更発生時のみ |

`project_plan`元スコープからの再定義: Phase 7(TRPG深掘り)/Phase 8(メディア生成)は明示的にpost-1.0へ送る(056のhistorical banner対象)。

### post-1.0 backlog(目的別epic、順序なし願望集にしない)

- **E-media**: 実画像provider・TTS・gallery・本文画像表示(041/043のprovider境界の上に載せる)
- **E-trpg**: map/location graph・NPC AI・reward・3つ目sample
- **E-ux**: Web review拡張(edit/rerun)・Web export/backup/init・rollback/branch Web化・onboarding強化
- **E-arch**: import cycle 1/2解消・state_manager/web service分割(060、CI計測gate導入後)
- **E-dist**: PyPI publish・非技術者配布・Windows native・plugin sandbox(ADR-0005/0004既定)

Release契約(ADR-0005)との整合: 矛盾なし — D3 post-1.0リストの具体化であり、mustの追加・削除はない。

### 承認事項

- 「1.0へ新機能ゼロ」の scope確定(本Issueの中核判断 — 人間承認必須)
- Web review拡張をshould(1.1)に置く判断
