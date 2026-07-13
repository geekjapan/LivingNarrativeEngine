---
id: 086
title: Action Outcomeをstate化して物語進展を保証する
status: todo
created: 2026-07-14
type: implementation
priority: P1
parent: 057
blocked_by: [085]
labels: [ready-for-agent]
---

# 086: Action Outcomeをstate化して物語進展を保証する

## Problem Statement

Issue 085の実LLM 30ターンrunは30/30ターンを完了したが、物語品質gateを通過しなかった。
主因はモデル品質ではなく、次の生成ロジックにある。

- キャラクターは「階段へ進む」「地上へ出る」と行動していたが、自由文Eventとして保存される
  だけでscene/world stateへ反映されなかった。
- 次ターンには古いscene状態が再投入され、同じ判断と行動が繰り返された。
- stall時のpressure boostはthreat pressureが100になると効果を失う。
- encounterは過去の発火履歴を参照せず、同じencounterを毎ターン選択できる。
- thread stateはnarrator出力だけに依存する一方、benchmarkはnarrator bindingを設定しておらず、
  thread更新が構造的に発生不能だった。
- 100ターンCI testはthread更新をbackfillする処理により、実runtime経路の欠陥を隠していた。

## Solution

キャラクターの自由文Actionとは別に、可視範囲内のscene affordanceを参照する構造化
Action Intentを生成する。ResolverはIntentを作者定義のaffordanceへ照合し、成立したOutcomeを
Event化する。状態変更は従来どおりStateDiffのみを通す。

進展経路は次の順序とする。

1. キャラクターが可視affordance IDを指定したIntentを提案する。
2. Resolverが前提条件、競合、必要なseeded rollを評価する。
3. 成功Outcomeがscene、fact、quest、thread等のStateDiffを生成する。
4. 同じターンに有効なOutcomeがなければ、stall時だけ作者定義fallback affordanceを使用する。
5. fallbackも成立しなければ、矛盾した物語を生成し続けず、診断付きで既存の停止・失敗経路へ
   入る。

## User Stories

### 1. キャラクター行動の永続化

キャラクターがscene内の出口、調査対象、対決対象などに対する行動を選んだとき、その結果が
次ターンの正本stateへ残らなければならない。

- 自由文だけを根拠にworld factを推測しない。
- Action Intentはvisibility-filter済みのaffordance IDを参照する。
- 成功Outcomeだけが状態を変更する。
- 次ターンのキャラクターとnarratorは更新後のscene状態を受け取る。

### 2. 作者定義affordance

コンテンツ作者は各sceneに、実行可能な行動とその結果を宣言できる。

- affordanceには識別子、表示範囲、対象actor、前提条件、成功判定、Outcome、消費・再利用規則を
  持たせる。
- Outcomeはscene transition、reader/canon fact、quest、threadなど、許可された状態効果だけを
  宣言できる。
- hidden条件や結果を、知らないキャラクターのpromptへ渡さない。
- LLMによる自由文semantic matchingは行わない。

### 3. 決定論的Action Resolution

同じstate、seed、Intent列からは同じOutcome、roll、StateDiffが得られなければならない。

- 競合時は既存のcharacter順序とcandidate順序を基準にする。
- chance判定は既存のseeded RNGを使い、roll artifactへ保存する。
- 不正または非合致のIntentは状態変更せず、reject理由をartifactへ残す。
- 自由文Action Event自体は従来どおり保存する。

### 4. stall時の接地済みfallback

有効なAction Outcomeが得られずstall windowへ達した場合、runtimeは作者定義fallbackだけを
使用できる。

- 任意のthreat stage、scene transition、threadをruntimeが創作してはならない。
- fallbackは少なくとも一つの認定されたadvancement StateDiffを生成する必要がある。
- Action Outcomeが成立したターンにはfallbackを重ねて発火しない。
- fallback発火もseed/replay対象とする。

### 5. pacing設定の事前検証

pacingを有効化するsceneは、有効なfallbackまたは明示的な終端契約を持たなければならない。

- 宣言漏れは実行前validationで検出する。
- fallbackが消費済み、前提不成立、進展効果なしの場合は`pacing_exhausted`診断を生成する。
- 新しいmeta statusは増やさず、既存のreview/failed契約とpartial artifact保存を使う。
- 固定ターンbenchmarkが必要数より前に終端へ到達した場合、そのrunはFAILとする。

### 6. encounter反復制御

encounterは`once`、`cooldown`、`unlimited`のrecurrence policyを持つ。

- eligibilityはappend-only Event履歴の`encounter_id`から決定する。
- policy未指定の既存projectは、pacing window以上のcooldownとして扱う。
- `unlimited`でも同一IDを連続ターンには選ばない。代替候補がなければそのターンはencounterを
  出さない。
- 既存templateではpolicyを明示する。
- 過去の保存済みreplayは変更しない。

### 7. state-firstなthread lifecycle

authored encounterまたはaffordance Outcomeは、reader-safeなthread open/advance/resolveを宣言
できる。

- authored threadは安定したIDとreader-visibleな説明を持つ。
- authored effectを一次正本とし、既存のStateDiffとthread update Eventを通して適用する。
- narratorは追加のemergent threadを提案できるが、authored effectと競合した場合はauthored側を
  優先する。
- authored thread更新があるターンでは、narratorによる重複openを拒否する。
- resolved threadへのadvanceなど、同一ターン内の矛盾をreject理由付きで保存する。

### 8. 正しい実LLM benchmark配線

実LLM品質gateはcharacterだけでなくnarratorも指定モデルへ明示的にbindしなければならない。

- 実行artifactからnarratorのLLM modeとcall数を確認できる。
- narrator fallbackが発生した場合はturn、理由、modeを記録する。
- ロジック変更前に、bindingだけを修正したbaseline runを新run IDで実施する。
- ロジック修正後は同じmodel、seed、評価契約で別runを実施する。

### 9. visibilityと秘密情報の維持

Intent、affordance、Outcome、thread、narrator contextの全経路で既存の情報scopeを維持する。

- hidden affordanceの識別子や条件を未認知characterへ渡さない。
- reader-visibleでないOutcomeからreader threadを開かない。
- GM情報をnarration、CLI、web、benchmark artifactへ含めない。
- rejected candidateにも秘密の値をそのまま記録しない。

### 10. 長期runでの回帰防止

CIは実LLMなしでも、今回の失敗を検出できなければならない。

- stall最大連続ターン、thread比率、encounter反復、scene進展を実runtime経路から計測する。
- test専用thread backfillでSLOを満たしてはならない。
- rollback、resume、backup restore後も同じOutcomeとroll列を再現する。
- 実LLM gateはCI testの代替ではなく、最終受入判定として残す。

## Implementation Decisions

- Action Intentは自由文解析ではなく、promptへ提示された可視affordance IDを参照する。
- affordanceに合致しないIntentは自由文Actionとしてのみ保存し、進展とは数えない。
- fallback判定はResolve段階まで遅延し、同じターンの通常Action Outcomeを優先する。
- advancementとして認めるのは、scene遷移・終了、reader/canon fact、quest進行、thread進行・回収、
  成功combatなど、永続stateを実際に変えるOutcomeに限定する。
- faction move、background event、pressure上限で変化しない更新はadvancementに数えない。
- authored thread effectをnarrator proposalより先に適用する。
- 永続的な責務変更であるため、Action Outcomeとthread ownershipについてADRを追加する。
- OpenSpecは使用しない。

## Testing Decisions

主回帰seamは、既存の100ターンfull pipeline smokeとする。

- thread backfillを除去し、Intent、affordance、Outcome、StateDiff、thread effectの実経路でSLOを
  満たす。
- 2回実行のreplay一致、rollback、15→16 resume、backup restoreを維持する。
- `max_consecutive_stall_turns <= 3`、thread resolved/opened比、max open turns、visibility、
  game機能発火を検証する。

短い敵対的integration testも追加する。

- structured Intentを出さないproviderからfallbackが発火する。
- fallback不在・消費済みで`pacing_exhausted`になる。
- Action Outcomeとfallbackが同一ターンに二重発火しない。
- encounterの各recurrence policyと連続発火抑止。
- authored/narrator thread競合とdedup。
- hidden affordance・thread情報が漏れない。
- 同じseedでEvent、roll、StateDiffが完全一致する。

最終受入は、`cx/gpt-5.6-luna-low`をcharacterとnarratorへbindした30ターンrunで、
ADR-0010の機械SLOとR1–R8をすべてPASSすることとする。

## Out of Scope

- モデル比較、fine-tuning、モデル固有prompt最適化
- 自由文Actionのsemantic解析
- LLM directorによる未定義scene・fact・threadの創作
- ADR-0010の閾値またはrubricの緩和
- web上のaffordance編集UI
- 既存projectを一括変換するmigration CLI
- OpenSpec導入

## Further Notes

- Issue 085の実行証跡とADR-0010を正本とする。
- binding-only baselineが機械SLOを通っても、encounter反復とAction/state分離は独立した構造欠陥
  であるため、本Issueのロジック変更範囲は維持する。
