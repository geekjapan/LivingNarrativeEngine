# ADR-0013: 作者定義Action Outcomeを状態進展の一次正本にする

## Context

Issue 085の実LLM 30ターンrunでは、キャラクターが移動・調査・対決を自由文で繰り返しても、
その行動はEventに残るだけでscene、fact、quest、threadの正本stateを変更しなかった。次ターンへ
同じstateが再投入されるため、narration上の移動と正本sceneが矛盾し、stallと反復が継続した。
また、thread進行をnarrator proposalだけに委ねると、narrator bindingや生成結果によって物語の
進展可否が変わり、作者が定義した因果を保証できない。

## Decision

1. キャラクターの自由文Actionと、状態変更を要求する構造化Action Intentを分離する。Intentは
   characterへvisibility-filter済みで提示した作者定義affordance IDだけを参照する。
2. Resolverはaffordanceのactor、前提、競合、消費状態、seeded chanceを検証し、成功時だけ
   `action_outcome` Eventを生成する。自由文Action Eventは物語上の記録として残すが、任意の
   free-text effectsを状態変更の根拠にしない。combatは既存の構造化検証経路を維持する。
3. Outcomeが宣言できる変更を許可済みStateDiff操作へ限定する。scene遷移、reader/canon fact、
   quest、thread、成功combat等の永続state変更だけをadvancementと数える。状態変更は引き続き
   StateDiffを通してatomicにcommitする。
4. stall時の自動進展は、作者がsceneへ宣言したfallback affordanceだけを使用する。通常Outcomeと
   同じturnに重ねず、fallbackが未定義・消費済み・前提不成立・非進展なら
   `pacing_exhausted`を記録し、既存のreview/failed経路へ入る。runtimeは未定義のscene、fact、
   threat stage、threadを創作しない。
5. authored Outcomeによるthread open/advance/resolveを一次正本とし、同じturnのnarrator proposal
   より先に投影する。重複open、resolved threadへのadvance等の競合は棄却し、理由をartifactへ
   残す。reader-visibleでないOutcomeからreader threadを生成しない。
6. affordanceの前提とOutcomeはcharacter promptへ渡さず、可視IDと安全な表示文だけを渡す。
   rejection、CLI/web、benchmarkへhidden条件や値を転記しない。

## Consequences

- 作者はsceneの進展経路、fallback、thread lifecycleをstate YAMLへ明示する必要がある。
- pacingを有効にした非終端sceneは、実行前validationで進展可能なfallbackを要求される。
- append-only Event、roll、StateDiffが同じstate/seed/Intentから再現でき、rollback、resume、backup
  restore後も同じOutcome列を検証できる。
- narratorは派生ビューとemergent thread proposalを担うが、作者定義の因果と競合した場合は
  authored Outcomeが優先される。
