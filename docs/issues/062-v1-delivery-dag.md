---
id: 062
title: 1.0実装DAGとrelease checklistを確定する
status: done
created: 2026-07-12
type: wayfinder:task
priority: P1
parent: 052
blocked_by: [053, 054, 055, 056, 057, 058, 059, 060, 061]
---

# 062: 1.0実装DAGとrelease checklistを確定する

## 問い

解決済みのsecurity、transaction、品質、UX、release engineering、architecture、feature scope判断を、並列実行可能で受入条件が独立した実装Issueと最終release gateへどう変換するか。

## 解決条件

- 各実装Issueが1つの検証可能なoutcomeを持つ
- blocking edge、並列lane、共有file conflictを記録する
- P0 security/reliabilityを最初のgateにする
- 100ターン品質、clean install、migration/recovery、UX受入を最終gateへ含める
- ADR作成点、GitNexus impact、実LLM、人手確認の必要箇所を明記する
- すべての子Issueをcloseし、このmapの`Decisions so far`を更新できる状態にする

## 関連ファイル

- `docs/issues/052-v1-release-wayfinder.md`
- `docs/plan/`
- `AGENTS.md`


## DAG(2026-07-13承認済)

新issue採番は064から。各issueは1つの検証可能outcomeを持つ。( )内は由来。

### Lane S: Web security(P0)

- **064** page.py innerHTML全面escape統一+grep guard test(054 must)
- **065** mutation API Origin検証(054 must)

### Lane T: transaction/recovery(P0)

- **066** `state/transaction.py`新設: flock+commit journal/hash+順序反転、driver/review統合、meta.yamlフィールド追加+migration連携(055-A+060(a))
- **067** recovery state machine+doctor CLI(055-B)← 066
- **068** fault injection+multiprocessテストmatrix(055-C)← 067
- **069** web/service.py settings/auto-run lock統合+auto_run.py抽出(060)← 066

### Lane Q: 品質gate

- **070** SLO測定基盤: metrics拡張+transition_count定義修正+rollback-RNG結合test(057-Q1)← 066(RNG pin/metaフィールド確定後)
- **071** 100ターンmock long-run fixture CI常設(057-Q2)← 070
- **072** 実LLM30ターンbench手順+benchmark artifact形式(057-Q3)← 070
- **073** β/1.0人手rubric文書(057-Q4)

### Lane U: UX受入

- **074** page.py最小UX/a11yパッチ+回帰test(058-A)← 064(page.py write競合)
- **075** disclosure leak-scan全endpoint横展開+player_character 403網羅(058-B)← 065(tests/web競合)
- **076** UX受入チェックリスト+人手smoke手順確定(058-C)← 074, 075

### Lane R: release engineering

- **077** CI hardening: --frozen/3.12+3.13 matrix/core-only job/web-extra import guard(059-A)
- **078** packaging+clean-install acceptance: wheel/Docker smoke/backup-restore/migration harness(059-B)← 080(βschema fixture pin)
- **079** pip-audit(release must/PR advisory)+coverage report-only(059-C)
- **080** release契約doc+CHANGELOG+release checklist+βschema凍結宣言(ADR+git tag)(059-E)← 066(meta schema確定後)、ADR承認
- **081** LICENSE選定+配置(059-D、**人間決定**)

### Lane D: 文書再同期(056)

- **082** DOC-P0/P1束: §29.6 web→serve修正+README導線+spec-foundation現行化+038/016整合(DOC-1/2/3/8)
- **083** DOC-P2束: project_plan banner+feature-dag banner+intervention/session-autonomy現行化(DOC-4/5/6/7)

### 依存edge(理由付き)

- 064→074、065→075: 同一file/test dirのwrite競合
- 066→067→068、066→069: lock/journal primitive依存
- 066→070→071/072: meta schemaとRNG pin確定が測定契約の前提
- 066→080→078: βschema凍結はmetaフィールド追加後、migration fixtureは凍結tagにpin
- 並列lane間はwrite scope非重複(S/T/Q/U/R/Dは主対象dirが分離)

### Gate構造

1. **Gate-P0**: 064-069完了+全test green(security/reliability最優先 — 052条件)
2. **Gate-β**: α(既達成)+077/078のclean install 2経路smoke+080のβschema凍結宣言+072手順による実LLM人手smoke 1回(073 rubric使用)
3. **Gate-1.0**: must全充足+migration regression(078)+実LLM品質gate(070-072)+UX受入(076+人手2セッション)+release checklist(080)+LICENSE(081)+v1.0.0 tag

### ADR発行計画(承認後に作成)

- ADR-0007: Web UI 1.0 security floor(054)
- ADR-0008: project transaction・排他・recovery契約(055)
- ADR-0009: 1.0前architecture debt範囲(060)
- ADR-0010: 実LLM品質ゲートと物語SLO(057)
- ADR-0011: release engineering baseline+βschema凍結形式(059)
- ADR-0012: License(**人間決定**)

### should(非gating、1.1候補backlog)

CSP header/plugin診断表示(054)、doctor拡張・--wait(055)、E2E拡張(058-D)、Web review edit/rerun(061)、転記自動化CLI(057)、DOC-P2は繰上げ可。

### 人手確認・実LLM・GitNexus必要箇所

- 人手: U3受入2セッション、実LLM smoke(β1回+1.0 gate)、LICENSE、各ADR承認
- 実LLM: 072(30ターンbench)のみ。他は全mock
- GitNexus impact: 066/069(cross-module)、064(web)で必須確認
