---
id: 056
title: Issue・計画・実装のcurrent truthを再同期する
status: review
created: 2026-07-12
type: wayfinder:research
priority: P0
parent: 052
blocked_by: []
---

# 056: Issue・計画・実装のcurrent truthを再同期する

## 問い

Issue 001〜051、完了済みDAG、凍結spec、企画書、README、現行code/testの矛盾と未証明条件をどう分類し、どの文書を現行仕様索引・歴史資料・将来ビジョンとして扱うか。

## 背景

全Issueは`done`だが、Issue 016の実LLM確認、Issue 038の`in_progress`記述、transition count、thread resolve、rollback RNG等に検証負債がある。`feature-dag-e7-e9.md`は途中時点のままで、`spec-foundation.md`と`project_plan.md`には実装済み機能を非目標とする歴史記述が残る。READMEも主要commandへの導線が不足する。

## 解決条件

- stale、historical、current、unverifiedを全関連文書で分類する
- 未チェック条件と既知制限をrelease blocker／品質改善／明示的非目標に分ける
- 現行仕様索引の置き場所と更新責任を決める
- α／β／1.0判定表へ根拠リンクを付ける
- 文書修正を小さな実装Issueへ切れる状態にする

## 関連ファイル

- `docs/issues/`
- `docs/plan/`
- `docs/spec-foundation.md`
- `docs/project_plan.md`
- `docs/session-autonomy.md`
- `docs/intervention.md`
- `README.md`


## 決定案(2026-07-13、承認待ち)

全文書をcurrent/historical/stale/unverifiedに分類済み(詳細は調査記録)。要点:

- **current(正本)**: spec-foundation §3-§8+§9の現行D群、plugin-sdk.md、rights-and-security.md、session-autonomy.md本文、ADR-0005。
- **stale(能動的誤り)**: project_plan §29.6 `living-narrative web`→実際は`serve`(**P0**)、§18.3ディレクトリ構成、§19 GitHub運用、§22 Issue番号表、spec-foundation §9 D108「plugin loaderは作らない」(049で出荷済)、intervention.md/session-autonomy.mdのbatch-time framing。
- **historical**: spec-foundation §1.3/§2のWeb非目標、D101/D109、project_plan §17.1/§20/§21/§27/Appendix、feature-dag両file。
- **unverified**: 016実LLM確認、038(frontmatter done vs 本文in_progress、quest resolve=0)、018 rollback後RNG再現、019 transition_count意味ずれ+thread 5起票0回収、008/010/013/014の実LLM未発火サブ条件。

### 決定

- **3分類**: release blocker=rollback後RNG完全再現の未固定(replay契約D3(ii)に接触 — 検証責任を057へ割当、gate前にmust/should確定)/ 品質改善=016・038・019ほか実LLM未発火群(057で実証)/ 明示的非目標=SQLite索引、画像・音声生成本体、sandbox、PyPI(ADR-0005既定)。
- **現行仕様索引**: 新規索引文書は作らない。README=ユーザー向けコマンド索引(CLI surface変更PRの完了条件に更新を含める)、spec-foundation §3-§8=規範契約(historical節に注記)、ADR-0005=gate正本。歴史文書は冒頭banner 1行で現行への導線のみ。
- **判定表**: 実体は052/062に置き、ADR-0005をリンク参照(複製禁止=§26事故の再発防止)。各セルにADR節+証拠(CI job/test path/smokeログ)+状態(green/pending+確認日)。α=機械検証のみ、β/1.0=人手attested項目を明示フラグ。

### 実装Issue分割(DOC-1〜8)

- DOC-1(P1): READMEコマンド導線拡充(metrics/rollback/branch/backup/restore+export全サブコマンド)
- DOC-2(**P0**): project_plan §29.6 `web`→`serve`修正
- DOC-3(P1): spec-foundation現行化(§3-§8を「現行契約」明示、historical注記)
- DOC-4(P2): project_plan stale/historical banner+Appendix B schema_version追記
- DOC-5(P2): feature-dag両fileへ完了履歴banner
- DOC-6(P2): intervention.md現行化
- DOC-7(P2): session-autonomy.md CLI TODO消化
- DOC-8(P1): 038 status/body整合+016へ057所管注記

rollback-RNG must/should確定と判定表構築はdoc-fixでなく057/062の設計項目として分離。
