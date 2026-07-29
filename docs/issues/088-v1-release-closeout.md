---
id: 088
title: v1.0出荷closeout — release checklist記入とv1.0.0 tag
status: open
created: 2026-07-29
type: release-validation
priority: P1
parent: 052
blocked_by: [089]
---

# 088: v1.0出荷closeout — release checklist記入とv1.0.0 tag

## 現在地（2026-07-29）

- Issue 001–085は`done`、086/087は`completed`。実装Issueのopen残はゼロ。
- 実LLM品質gate（Issue 070–072、ADR-0010）は`20260727-issue086-r4-hardening`
  （revision `48f4c0e`）で機械SLOとR1–R8が全PASS。
- Gate-P0（064–069）とGate-βの自動検証部（077/078/079のCI）は継続green。
- `beta-schema-v1` tagはorigin push済み。LICENSE（MIT、ADR-0012）配置済み。
- 未達はrelease checklist（`docs/release-checklist.md`）の記入と、以下の残作業のみ。

## 完了条件

- [ ] β gate全項目に証跡（CI run URLまたはファイルパス）を記入しcheckする。
      実LLM smokeは`20260727-issue086-r4-hardening`の証跡を流用してよい。
- [ ] UX受入2セッション（`docs/ux-acceptance-checklist.md`のSession 1/2、**人間実施**）を
      release候補で実施し、記録を`docs/evaluations/`へ保存する。
- [ ] 実LLM 30ターンgateをrelease候補revision（HEAD）で再実行しPASSさせる
      （2026-07-29決定: run ID `20260729-issue088-rc-gate`、seed `issue-085-mist-station-v1`、
      `cx/gpt-5.6-luna-low`をcharacter+narratorへbind。前提: OmniRoute gateway起動。
      実行環境ブロックの詳細と再開手順はIssue 089）。
- [ ] `pip-audit`のrelease時blocking checkを実行し記録する（coverageはreport-only）。
- [ ] `CHANGELOG.md`の`Unreleased`を`1.0.0`へ移し、日付と比較対象を記録する。
- [ ] `pyproject.toml`のversionを`0.1.0`→`1.0.0`へ更新する。
- [ ] 1.0 gate全項目をcheckし、annotated tag `v1.0.0`を作成・pushする。
- [ ] wheel/sdist/tagged Dockerfile local buildを確認し、GitHub Releaseへwheel/sdistを
      添付する（PyPI pushはpost-1.0のため行わない）。

## 依存関係

- 先行（すべて完了済み）: 052→053–062（判断）→064–083（実装）→085（gate FAIL）→
  086/087（構造修正とgate PASS）。
- 本Issue内の順序: UX受入・pip-audit・RC差分確認 → CHANGELOG/version bump →
  checklist記入 → tag/Release。UX受入とtag pushは人間ゲート。
- 正本: `docs/release-checklist.md`（判定記録）、ADR-0005/0010/0011（契約）。

## Out of scope

- post-1.0 backlog（Issue 061の5 epic: E-media/E-trpg/E-ux/E-arch/E-dist、
  062のshould項目）。1.0出荷後に別Issueで着手する。
- PyPI/registryへのpublish、閾値・rubricの変更。

## 関連ファイル

- `docs/release-checklist.md`
- `docs/ux-acceptance-checklist.md`
- `docs/issues/086-state-backed-action-outcomes.md`
- `docs/issues/087-t9-quality-gate-follow-up.md`
- `docs/evaluations/2026-07-27-20260727-issue086-r4-hardening-*.md`
- `CHANGELOG.md`、`pyproject.toml`
