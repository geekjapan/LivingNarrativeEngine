---
id: 052
title: 1.0リリース準備の道筋を確定する
status: open
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

