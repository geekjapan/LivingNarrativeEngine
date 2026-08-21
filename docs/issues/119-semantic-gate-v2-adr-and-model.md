---
id: 119
title: Semantic Gate v2のADR・evidence schema・hard/soft判定を実装する
status: completed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [118]
labels: [long-form, quality, continuity, semantic-gate]
---

# 119: Semantic Gate v2のADR・evidence schema・hard/soft判定を実装する

## 背景

v0.3.0のsemantic continuity gateは、必須threadの未被覆をblockし、LLM由来のfindingへevidenceとrepair instructionを保存する。しかし、数十万字級の品質判断には、人物arc、視点、伏線/謎、act promiseに対して、**どのreader-safe根拠から、何を、どの厳格さで修正するか**を明示する安定した評価契約が必要である。

## 公開seam

`evaluate_semantic_continuity(context, candidate, gateway=...)`を後方互換に維持し、v2では返却する`SemanticContinuityAssessment`を深める。callerは一つのassessmentだけを受け取り、finding category、severity、evidence、repair instruction、対象ID、決定的なcoverage不足をreview artifactから説明できる。

## 完了条件

- [x] finding category、evidence source、subject ID、repair instructionを含むv2 reader-safe schemaを導入した。
- [x] required threadとchapter計画済みcharacter arc targetの未被覆を決定的blockとして追加した。
- [x] POV・人物関係・foreshadowing/謎・act promiseは、evidenceを持つmodel findingとしてwarn/blockを記録できる。
- [x] modelはreader-safe contextだけを受け取り、plan obligationを免除できない。
- [x] legacy v1 responseを受け取れる互換readerとmigration不要のreview artifactを保った。
- [x] category別のblock/warn、repair evidence、prompt disclosure、review decisionをfocused testで固定した。

## 非対象

act/arc/characterの階層summary永続化、blind editorial rubric、finding別のrevision policy、20〜30章E2Eは後続Issueへ分離する。
