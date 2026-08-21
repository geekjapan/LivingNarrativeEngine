# ADR 0016: Semantic Gate v2をreader-safe evidenceと決定的obligationで深める

- **Status:** Accepted
- **Date:** 2026-08-21
- **Decision owners:** LivingNarrativeEngine maintainers
- **Related:** Issue 119, ADR 0014, ADR 0015

## Context

v0.3.0の`evaluate_semantic_continuity()`は、candidate本文とreader-safe章contextからLLM findingを取得し、BookPlanのrequired thread未被覆を決定的blockとして追加する。この契約は安全だが、人物arc、視点、伏線/謎、act promiseを長編品質の判断対象として説明するには、findingの分類、根拠の由来、対象、修復指示、hard/softの意味を安定化する必要がある。

> 品質gateは本文を生成する権限ではない。reader-safeな入力から根拠付きfindingを作り、著者がaccept/reviseを判断できるreview artifactを残すための評価器である。

## Decision

### 1. 一つのdeep seamを維持する

外部interfaceは引き続き`evaluate_semantic_continuity(context, candidate, gateway=...) -> SemanticContinuityAssessment`とする。callerへcategoryごとの複数evaluatorやprompt組立てを露出しない。v2の複雑さはreview moduleの内部へ閉じ込め、`review_chapter()`は`block` findingだけをrevision理由へ変換する。

### 2. findingはreader-safeなevidence contractを持つ

各findingは`category`、`severity`、`evidence`、`repair_instruction`、`subject_ids`、`evidence_sources`を持つ。`evidence`はcandidate、chapter plan、continuity digest、reader factsのいずれかへ説明可能に結び付く短いテキストであり、GM-only state、prompt全文、credential、absolute pathを含めない。categoryは`required_thread`、`character_arc`、`point_of_view`、`character_relation`、`foreshadowing`、`act_promise`、`other`に限定する。

### 3. BookPlan obligationはmodelが免除できない

required threadとchapter planに含まれるcharacter arc targetは、assessmentのcoverage listと突き合わせる。未被覆は必ず`block` findingとして追加する。LLM responseのseverityや「問題なし」という主張は、この決定的checkを上書きできない。

### 4. その他の品質findingは根拠付きwarn/blockで保存する

POV、人物関係、伏線/謎、act promiseは、v2 model responseがreader-safe根拠とrepair instructionを伴うfindingとして返す。severityはreviewに保存し、`block`だけが既存の`review_chapter()`を`revise`へ進める。誤検出を減らすため、hard ruleを追加するのはBookPlanまたはreader-safe ledgerに明確なobligationが導入された場合に限る。

### 5. v1 review artifactを読み続ける

新規fieldはdefaultを持つ。既存の`code`、`severity`、`evidence`、`repair_instruction`とv1 gateway responseは有効なv2 assessmentへparseされる。Book State migrationは行わず、review/attempt artifactはPydanticのdefaultによってread compatibilityを保つ。

## Consequences

| 項目 | 採用する結果 | 採用しない結果 |
|---|---|---|
| 透明性 | findingごとにcategory、対象、根拠、修復が残る | opaqueな総合scoreだけで著者へ改稿を要求しない |
| 安全性 | promptとreview artifactはreader-safe projectionを使う | private/GM-only stateを品質精度のためにgateへ送らない |
| 制御 | plan obligationは決定的block、その他はevidence付きseverity | LLMがrequired thread/arcを任意に免除しない |
| 互換性 | legacy responseとartifactを既存field/defaultで読む | v0.4のためだけにBook State schema migrationを導入しない |

## Rejected alternatives

1. **LLM score一つでaccept/reviseを決定する。** 根拠、再現性、著者の異議申立てが失われる。
2. **全品質項目をhard blockにする。** POVや伏線の曖昧な判断の偽陽性が改稿負債を増やす。
3. **品質を高めるためGM/private dataを入力する。** disclosure boundaryとreader-safe artifactの契約に反する。
4. **categoryごとに新しい公開CLI/APIを作る。** callerがprompt、order、error handlingを知る浅いinterfaceになり、review moduleのlocalityを失う。

## Verification

focused testsはlegacy v1 response、required thread/arcの決定的block、category別warn/block、reader-safe prompt、review decisionを固定する。後続Issueで階層summary、blind benchmark、revision policy、20〜30章E2Eを同じassessment artifactに接続する。
