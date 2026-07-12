---
id: 053
title: 1.0の利用者・配布形態・受入基準を固定する
status: done
created: 2026-07-12
closed: 2026-07-12
type: wayfinder:grilling
priority: P0
parent: 052
blocked_by: []
---

# 053: 1.0の利用者・配布形態・受入基準を固定する

## 問い

ローカル単一利用者向け1.0は誰のどの体験を保証し、uv／Docker／packageのどの配布経路を正式対応とし、どの実測条件を満たしたら出荷可能と判定するか。

## 背景

Phase 7〜9とIssue 001〜051は完了している一方、`project_plan`のα／β／1.0定義は定性的で、E9完了と1.0完成が混同されている。現状は機能豊富なpre-βであり、次の作業を選ぶために目的地を先に固定する必要がある。

## 解決条件

- [x] primary personaと代表ユーザージャーニーを1つに絞る → D1
- [x] 正式対応するinstall／起動／upgrade経路を決める → D2a/D2b
- [x] must／should／post-1.0を判定する原則を決める → D3
- [x] α／β／1.0を自動検証可能・人手評価可能な条件へ置換する → D4
- [x] trusted in-process pluginとprovider境界を1.0へ含める範囲を決める → D5

## 決定台帳(assisted grilling、2026-07-12)

- **D1** [human] primary persona = 技術中級の一人遊び物語シミュレーション愛好者。
  代表ジャーニー: install → init → serve → Web UI観測+介入 → export。
  開発者CLI/非技術者配布/PyPI/GUIインストーラはnon-gating。
- **D2a** [delegated] 正式経路: install=`git clone`+`uv sync --extra web` /
  `docker compose up`。起動=`init`+`serve`。upgrade=`git pull`+`uv sync`
  (or `compose pull/build`)+schema_version自動migration。
- **D2b** [human] migration互換保証: βschema→1.0を保証、α以前はbest-effort。
- **D3** [human] must=(i)ジャーニー完走不能/(ii)データ損失・replay破壊・disclosure漏洩・
  plugin trust侵害/(iii)公開契約(schema/CLI/export)を破るhard-to-reverse。
  should溢れ→1.1.0。post-1.0=派生レイヤ・sandbox・PyPI。patch=互換修正のみ。
- **D4** [human] gate構造: α=遡及認定(全test green+mock journey E2E CI)。
  β=α+2経路install smoke+βschema凍結+実LLM人手smoke 1回。
  1.0=β+must全充足+migration regression+057/058/059 gate+v1.0.0。
- **D5** [human] 1.0公開契約=allowlist設定形式+transactional登録、provider設定面。
  experimental=plugin SDK API、provider protocol。

詳細と帰結はADR-0005(リリース契約)とADR-0006(stability tier)を正本とする。

## 派生作業

- Issue 063: mock provider journey E2E test(D4の唯一の新規実装must)。
- Issue 057: βの実LLM人手smoke合否基準としてrubric簡易版を定義する(解決条件へ追記済み)。
- Issue 059: βschema凍結の宣言形式(git tag/文書)を決める(解決条件へ追記済み)。

## 関連ファイル

- `docs/adr/0005-v1-release-contract.md`
- `docs/adr/0006-plugin-provider-stability-tiers.md`
- `docs/project_plan.md`(§26置換済み)
- `docs/adr/0004-explicit-plugin-allowlist-trust-boundary.md`
