# ADR-0010: 実LLM長期品質ゲートと物語SLO

## Context

β条件の100ターンは未証明で、rollback後のRNG再現は結合testのない条件付き保証、
transition_countは論理遷移の約2倍を計上する。実LLM自動テストはCIにゼロ件(Issue 057)。

## Decision

1. **役割分担**: mock 100ターン=CI常設回帰gate(機械pass/fail)。実LLM 30ターン=β・1.0 gate時+
   リリース前定点観測(CI常設しない)。人手読解=実LLMラン抜粋15ターンをrubric判定。
2. **gate SLO(機械閾値)**: replay完全一致(mock 100×2回)/rollback後RNG決定性(結合test)/
   `max_consecutive_stall_turns`≤3/thread resolved比≥0.5かつ`max_open_turns`≤25/
   leak findings(critical/high)=0/`max_consecutive_at_ceiling`≤5/game機能発火>0/
   論理遷移数比率/cost・time budget(初期値は仮固定、運用調整可)。
   人物同定・narrator identity・motif反復は観測のみ(gate外、人手rubricへ)。
3. **scene transition論理定義**: 旧+新のstatusペア1組=1遷移。metrics.pyの計数を修正し、
   既存test期待値をセットで更新する(破壊的変更として本ADRに記録)。
4. **rollback後RNG再現はmust**(replay必須契約)。rollback→次turnのroll列一致を結合testで固定する。
5. **long-run journey**: init→40turn→export→snapshot→介入分岐→rollback→再進行→100turn→
   最終export→backup-restoreからresume。既存パターンの合成のみ。
6. **β人手rubric(8項目YES/NO、1つでもNOでfail)**: 継続性矛盾なし/GM情報漏洩なし/
   thread≥1回収/人物同定/同一フレーズ3連続反復なし/感情整合/game機能≥1発火/
   rollbackまたはresume正常動作。ADR-0005 D4の「057 rubric簡易版」の参照先は本表とする。

## Consequences

- 1.0出荷可否は機械SLO+人手rubricの全passに還元される。
- transition_count定義変更により過去のmetrics値と比較不能になる(artifactに定義版を記録)。
- benchmark artifactはsandbox実行+JSON+`docs/evaluations/`転記の現行方式を維持する。
