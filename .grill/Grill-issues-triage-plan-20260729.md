# Grill — Issue全件確認後の整理計画 (20260729)

対象: 086-delivery-plan status更新、release-checklist PASS証跡追記、Issue 088作成。

## 自己解決済みの主な論点

- statusの語彙: 001–085は`done`、086/087は`completed`。086-delivery-planは多数派の
  `done`へ更新（両語彙が混在するが実害なしのため統一作業はしない）。
- Issue採番: 086がparent（`086-state-backed-action-outcomes.md`）とchild
  （`086-delivery-plan.md`、id=`086-delivery-plan`）で番号を共有。次番は088で衝突なし。
- release checklistのcheckbox: 出荷判定時の記録であるため今回は触らず、証跡パスのみ追記。
  記入はIssue 088の実行に含めた。
- `beta-schema-v1` tag: `git ls-remote`でorigin push済みを確認（`b17f72a2`を指すannotated tag）。
- UX受入記録: `docs/evaluations/`にSession 1/2の記録なし → 未実施として088へ計上。
- CHANGELOG/version: `Unreleased`のみ・`0.1.0`のまま → 088へ計上。

## Issue全件確認後の整理計画 — Grill残課題 (20260729)

### Q1. 実LLM品質gateのPASS証跡がrelease候補revisionと一致しない

- **対象**: `docs/release-checklist.md` 1.0 gate「Issue 070–072のSLO・実LLM品質gate」、
  `docs/issues/088-v1-release-closeout.md`のRC差分確認タスク
- **なぜ重要**: gate PASS run（`20260727-issue086-r4-hardening`）はrevision `48f4c0e`で実施
  されたが、HEADまでに`src/living_narrative/narration/context.py`へ挙動変更
  （thread origin判定のevent読込をopening turnへ限定）が入っている。1.0 tagをHEADで打つと、
  gate証跡と出荷物のnarration挙動が厳密には一致しない。
- **自己調査**: `git diff 48f4c0e..HEAD -- src/`で確認。`pacing.py`はdocstringのみ、
  `narration/context.py:60-78`は実挙動変更。ADR-0010にRC revisionでの再実行義務の明文は
  なし（grep「再実行|rerun」該当なし）。再実行にはOmniRoute gateway到達性と約49万token・
  約15分のコストが掛かるため、費用対効果の判断はユーザーに属する。
- **検討した選択肢**: A) `48f4c0e`の証跡をそのまま受理してHEADでtag /
  B) HEADで実LLM 30ターンrunを再実行してからtag / C) `48f4c0e`をrelease候補commitにして
  tag（以降のcommitは1.0.1へ）
- **推奨案**: B。変更がgateの測定対象そのもの（narrator context）に入っているため、
  同一seed/model/bindingで1回再実行するのが最も安全。差分が小さくreplay系SLOは既にCIで
  担保されるため、FAILリスクは低い。
- **不足インプット**: 再実行コストを許容するか、A/Cで済ませるかの判断。
- **Status**: Resolved — B採用。HEADを release候補とし、同一seed/model/bindingで実LLM 30ターンrunを
  新run ID `20260729-issue088-rc-gate`として再実行する (docs/issues/088-v1-release-closeout.md)

### Q2. v1.0出荷（UX受入2セッションとtag push）の実施タイミング

- **対象**: `docs/issues/088-v1-release-closeout.md` 完了条件のUX受入・tag/Release項目
- **なぜ重要**: UX受入2セッション（ADR-0005 persona準拠）とv1.0.0 tag pushは契約上の
  人間ゲートで、agent側で代行するとgateの意味が失われる。
- **自己調査**: `docs/ux-acceptance-checklist.md`でSession 1/2が人手実施と明記。
  `docs/evaluations/`に実施記録なし。実施日程・担当は文書からは決められない。
- **検討した選択肢**: A) Q1解決後すぐユーザーが2セッション実施 / B) 当面βのまま運用し
  出荷を保留
- **推奨案**: A。品質gate PASSで技術的blockerは消えており、遅らせる理由は文書上ない。
- **不足インプット**: UX受入セッションの実施可否と時期。
- **Status**: Resolved — 実施決定。gate再実行PASS後の同一release候補でSession 1/2を実施する
  (docs/issues/088-v1-release-closeout.md)
