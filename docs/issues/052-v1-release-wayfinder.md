---
id: 052
title: 1.0リリース準備の道筋を確定する
status: done
created: 2026-07-12
type: wayfinder:map
---

# 052: 1.0リリース準備の道筋を確定する

## Destination

現行のIssue 001〜051と実装済み機能を起点に、ローカル単一利用者向け1.0の出荷可否を判断できる受入基準、アーキテクチャ判断、実装依存DAG、release checklistが揃っている状態にする。

## Notes

- このmapは計画専用であり、個別機能の実装は行わない。最後に実装Issueへ変換する。
- ユーザー確認前の仮定として、次の目的地は「新機能追加」ではなく「ローカルファースト1.0の安定出荷」とする。
- 正本の優先順位は`AGENTS.md`に従い、code/test、Issue/ADR、`docs/spec-foundation.md`、`docs/project_plan.md`の順で現行性を判断する。
- 必須契約（StateDiff、visibility、seed決定性、partial artifact、Pydantic正本、plugin trust boundary、disclosure-safe出力）は維持する。
- 子Issueは`rg -l '^parent: 052$' docs/issues`で列挙できる。`blocked_by`が空のopen Issueが現在のfrontierである。
- 2026-07-12の基準値: Python 3.13.13、951 tests pass、ruff lint/format pass、`git diff --check` pass。GitNexusは409 files / 6,600 symbols / 300 flows、import cycle 2件を検出。

## Decisions so far

<!-- closed child Issueの結論だけを1行で追記し、詳細は子Issueに置く -->

- 053: 1.0契約確定 — persona=技術中級一人遊び、経路=uv/docker、βschema→1.0 migration保証、must原則とα/β/1.0 gate構造(ADR-0005)、plugin/provider stability tier(ADR-0006)。新規must実装=063 mock journey E2E。
- 054: security floor確定 — innerHTML全面escape+grep guard+Origin検証=must、CSP/plugin診断=should、TrustedHost/sandbox/認証=post-1.0(ADR-0007)。
- 055: transaction契約確定 — flock排他+commit journal(hash/rng-offset)+順序反転=must、recovery state machine+doctor、fault/multiprocess test matrix(ADR-0008)。
- 056: current truth再同期 — 3層索引(README/spec-foundation §3-§8/ADR-0005)、stale/historical分類確定、DOC-1〜8を082/083へ、rollback-RNG検証は057所管。
- 057: 品質gate確定 — mock 100ターンCI常設gate+実LLM30ターンβ/1.0時+人手rubric 8項目、rollback-RNG結合test=must、transition論理定義修正(ADR-0010)。
- 058: UX受入確定 — Web必須=turn/介入/review/停止再開/観測、init/export/backup=CLI+導線でmust充足、最小page.pyパッチ、人手2セッション評価。
- 059: release engineering確定 — --frozen+import guard+Docker/wheel smoke、βschema凍結=ADR+git tag、SemVer(ADR-0006)、LICENSE=人間選定(ADR-0011)。
- 060: architecture debt範囲確定 — state/transaction.py=唯一のcommit境界、auto-run抽出まで1.0、cycle解消/分割はpost-1.0計測付き延期(ADR-0009)。
- 061: scope確定 — 1.0新機能ゼロ。post-1.0はE-media/E-trpg/E-ux/E-arch/E-distの5 epic。
- 062: 実装DAG確定 — issue 064-083、6 lane、Gate-P0→Gate-β→Gate-1.0、ADR-0007〜0011発行。

## Not yet specified

- 1.0の具体的な物語品質SLO、実LLM評価モデル、許容費用はRelease契約と品質ゲートの決定後に確定する。
- Web UIの改修幅は、代表ユーザージャーニーの観察結果が出るまで分割しない。
- 実画像/TTS provider、3つ目の実用sample、TRPG深掘りを1.0へ含めるかは、品質・UX評価後に決める。
- transaction設計確定後に、fault injection、migration、backup/restore、rollbackをどの実装Issueへ分けるか決める。
- 公開packageの配布先、license、support期間、release cadenceはRelease契約とrelease engineering調査後に確定する。

## Out of scope

- このmap内での実装、commit、release、外部公開。
- マルチユーザー／オンラインTRPG、公開インターネット向けhosting、production運用。
- 完全自動の出版品質長編、商用ゲームエンジン、MMO型永続world。
- 凍結済みOpenSpecの再導入や全面同期。
- 根拠のない全面rewrite。

