# ADR 0017: Cost Policy v2の料金snapshot・予算評価・停止責務

- **状態:** Accepted
- **日付:** 2026-08-21
- **対象リリース:** v0.5.0 Production Governance & Publication

## 文脈

既存の`BookBudgetPolicy`はchapter/book/revision回数だけを事前評価する。長編制作では、providerごとのtoken単価、estimateとactual、chapter/act/book予算、soft warningとhard stopを同じ監査契約の下で扱う必要がある。一方で、実費の追跡はprovider固有のusage欠落や価格改定を伴うため、未確定のusageを成功費用として扱ってはならない。

## 決定

Cost Policy v2は、reader-safeな`evaluate_cost_policy(...) -> CostPolicyAssessment`を唯一のdeep seamとする。この評価は副作用を持たず、`allow`、`warn`、`block`の判断、対象scope、reason、estimateを返す。draft providerの呼出し可否は、`block`である場合にのみ既存の`BudgetExceededError`へ接続する。既存のattempt回数上限は互換性のため`BookBudgetPolicy`に残し、新しいtoken/USD評価はオプトインの`CostPolicyV2`で追加する。

料金はUSD建てのimmutableな`PriceSnapshot`で表し、`profile_id`、`version`、input/output token単価、税率、割引率を持つ。通貨換算を導入せず、料金のversionを後から書き換えない。計算は`Decimal`を利用し、丸めは表示境界だけに閉じ込める。

| 予算値 | 評価対象 | 用途 |
|---|---|---|
| soft cap | chapter / act / book | 著者へ警告を表示するが、provider呼出しは許可する。 |
| hard cap | chapter / act / book | 予測costがcapを超える場合、provider呼出しを0回にする。 |
| estimate | 予定input/output token | provider呼出し前の可否判定とforecastに用いる。 |
| actual | providerが記録したusage | usage attributionと実績報告にのみ用いる。 |

unknownな価格またはusageは`CostPolicyAssessment`で明示的に`unknown`とし、actual costへ合算しない。hard capに対し価格または予測が未知なら、fail-closedで`block`とする。soft capだけの場合はwarningを返すが、著者の明示的なproduction実行を妨げない。

Cost Policyはaccept/reviseを自動化しない。budgetによる停止後も、設定を更新した著者が既存のresumeフローを明示実行する。

## 結果

料金・予算判断は、provider adapterやWeb層でなくBook domainに局所化される。後続Issue 124はactual usageをrun/attempt/act/bookへ帰属し、Issue 125はこのassessmentをreader-safeなCockpit表示へ投影する。料金snapshotとassessmentはcredential、prompt、本文、private/GM dataを含まない。

## 却下した案

providerごとに評価ロジックを実装する案は、価格versionとhard-stopの一貫性を失うため採用しない。floatでUSDを計算する案は丸め誤差と比較境界の不安定さを生むため採用しない。unknown priceを0 USDとして通過させる案はhard capを無効化するため採用しない。
