# LivingNarrativeEngine — Issue 097〜103 実装成果

**用途:** 開発レビュー、アーキテクチャ説明、次期投資判断
**推奨時間:** 15〜20分
**想定聴衆:** プロダクト責任者、技術リーダー、長編制作ワークフローの運用担当者

## Cover

**タイトル:** LivingNarrativeEngine: 長編制作を「追跡・検証・出荷」できる基盤へ
**サブタイトル:** Issue 097〜103 実装成果と次マイルストーン
**発表者:** Manus AI / 2026-08-18

## Slide 1

**タイトル:** 長編生成の課題は「本文生成」だけではない

- 改稿で失われる履歴、章間の不整合、無制限retry、未検証の原稿出荷が運用を壊す。
- 必要なのは、生成品質だけでなく**状態・証跡・品質・出荷**を一貫して管理する制作基盤である。
- 今回はIssue 097〜103で、制作ライフサイクルの監査可能な骨格を実装した。

**話す要点:** 商業規模の長編では、モデル能力に加え、失敗から復旧し、品質と出荷物を説明できることが必要である。
**推奨ビジュアル:** 6つの課題を「履歴／継続性／予算／操作／出荷／測定」の六角形で配置。

## Slide 2

**タイトル:** 今回の到達点: 制作の正本を分離した

- **状態正本:** BookPlan・BookLedger・StateDiff・transaction journal。
- **制作artifact:** draft request/prompt/response、candidate、review、immutable attempt。
- **消費系:** Cockpit、manuscript export、benchmarkは正本を直接書き換えない。

> 「何が起きたか」を状態遷移で、「なぜそうなったか」をartifactで追跡する。

**話す要点:** UIやexportを正本にしないことで、運用画面の変更や出力形式追加が物語状態を壊さない。
**推奨ビジュアル:** 三層アーキテクチャ図（State / Artifacts / Consumers）。

## Slide 3

**タイトル:** 章は明示的なlifecycleで進む

- `planned → running → candidate → review → accepted` を明示的に管理。
- reviewで問題があれば `revising → 次attempt` に戻り、過去の試行は保持する。
- 無効遷移はcoordinatorで拒否し、Web APIでは409として扱う。

**話す要点:** 成功だけでなく、改稿や停止をfirst-class stateにした点が重要である。
**推奨ビジュアル:** lifecycle state machine。acceptは緑、reviseは橙、blockは赤で表現。

## Slide 4

**タイトル:** Issue 097: 改稿を失わないimmutable lineage

- candidate本文hashを基に、各試行を`ChapterAttempt`として不変保存する。
- review、draft run、親attemptを紐づけ、改稿の系譜を追跡できる。
- accept時は「最新版」ではなく、検証済みの**accepted attempt pointer**を確定する。

**話す要点:** 再生成による上書きを排し、「どの本文が、どのreviewを通ったか」を永続的に説明できる。
**推奨ビジュアル:** attempt_001 → attempt_002 → attempt_003の分岐・accept pointer図。

## Slide 5

**タイトル:** Issue 099・098: 継続性を次章へ接続する

- accepted本文からreader-safeかつ上限付きのcontinuity digestを導出する。
- 未回収threadをledgerで追跡し、次章のdraft promptとsemantic reviewへ同じ情報を渡す。
- required threadの未被覆はsemantic blockとなり、acceptを止める。

**話す要点:** 長編の一貫性を「前章を丸ごと読む」方式ではなく、監査可能な圧縮情報と未解決課題で保つ。
**推奨ビジュアル:** Accepted chapter → Digest / Open threads → Next draft & review の循環図。

## Slide 6

**タイトル:** Issue 100: 無制限retryを回路遮断する

- chapter単位・book単位のattempt上限と、連続改稿上限を導入した。
- provider呼出し**前**に決定的preflightを実施する。
- 超過時は`circuit_breaker.yaml`に停止理由を残し、費用だけを増やす再試行を防ぐ。

**話す要点:** 失敗を黙って繰り返さず、止まった理由をartifactとして残す。
**推奨ビジュアル:** Provider call前のgateを強調したcontrol-flow図。

## Slide 7

**タイトル:** Issue 101: Cockpitは状態を直接編集しない

- roadmap、lifecycle、next actionをreader-safeに投影する。
- UIが行うmutationは、開始・承認・改稿の3操作に限定する。
- すべてpermission、transaction lock、coordinatorを経由し、操作後は状態を再読込する。

**話す要点:** 便利なWeb画面ではなく、正本境界を守る「制作コックピット」として設計した。
**推奨ビジュアル:** UI → API → Service → Coordinator → StateDiffの一方向フロー。

## Slide 8

**タイトル:** Issue 102: 出荷できるのはaccepted原稿だけ

- exporterはBookPlan順にaccepted lifecycleとaccepted attempt pointerを照合する。
- 未accept章やpointer欠落があれば、原稿化を明示的に失敗させる。
- `manuscript.md`とhash付き`manuscript_manifest.yaml`をatomicに出力する。

**話す要点:** 「生成された本文」ではなく「レビュー済みの本文」だけを配布可能な原稿と定義する。
**推奨ビジュアル:** accepted attempts → manuscript.md + manifest の出荷パイプライン。

## Slide 9

**タイトル:** Issue 103: 長編の進捗と同一性を測定する

- benchmarkはBook stateとimmutable lineageを**読取り専用**で集計する。
- 章数、accepted/revising/block中章数、attempt数、open thread数、fingerprintを公開する。
- 本文、prompt、credential、絶対パスをreportへ含めない。

**話す要点:** benchmarkは品質の自動採点器ではない。制作の進捗・負債・artifact変化を比較可能にする観測装置である。
**推奨ビジュアル:** 入力（state + lineage）→ safe aggregate → JSON report のデータフロー。

## Slide 10

**タイトル:** 実測: 9章計画を安全に観測できた

| 指標 | `transmigrated-crown` 実測値 | 意味 |
|---|---:|---|
| planned chapters | 9 | 長編計画の規模 |
| accepted chapters | 1 | 原稿化可能な章 |
| attempt count | 0 | Issue 097導入前acceptのためlineage未作成 |
| open thread count | 0 | continuity上の未回収負債 |
| artifact fingerprint | `b865…9621` | 本文を出さない同一性指標 |

**話す要点:** legacy章のattempt数が0なのは、履歴を捏造しない正本方針の結果である。次の実装では検証付きbackfillを行う。
**推奨ビジュアル:** 数値カード5枚と「legacy lineage backfill」への注釈。

## Slide 11

**タイトル:** 次の投資は「自律化の前に観測可能性」を完成させる

- **優先度A:** Production Runner、legacy lineage backfill、benchmark CLI/CI。
- **優先度B:** Semantic Gate v2、act/arc/characterの階層summary、編集評価benchmark。
- **優先度C:** token/USD予算、DOCX/EPUB/PDF adapter、publication manifest、persistent worker。

**話す要点:** 先に試行と品質を測定できるようにしてから、より長い自律runとコスト最適化へ進む。
**推奨ビジュアル:** A→B→Cの3段階ロードマップ。各段階に「運用可能化」「品質安定化」「出荷・スケール化」を付与。

## Slide 12

**タイトル:** 結論: 生成を「監査可能な長編制作」へ変えた

**サブタイトル:** 次は、Production Runner・lineage backfill・benchmark CIで9章計画を完全な制作証跡へ育てる。

---

## 発表設計メモ

| 項目 | 推奨 |
|---|---|
| 枚数 | 13枚（Coverを含む） |
| 所要時間 | 15〜20分、質疑を別途5分 |
| デザイン | ダークエディトリアル。state/transactionは青、acceptedは緑、review/reviseは橙、blockは赤。 |
| 強調する数値 | 1107 passed / 2 skipped、9 planned chapters、1 accepted chapter。 |
| 省略候補 | 時間が10分の場合はSlide 4・5を1枚に、Slide 7・8を1枚に統合する。 |
