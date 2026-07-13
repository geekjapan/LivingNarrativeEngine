# ADR-0009: 1.0前architecture debt範囲の凍結

## Context

GitNexusはimport cycle 2件を検出したが、いずれも実行時ImportErrorを起こさない
(cycle 1は意図的な依存逆転、cycle 2は型の置き場所の問題)。責務集中
(state_manager 899行、web/service 792行)はあるが、全面refactorはrelease riskになる。
ADR-0008の実装場所の確定が必要(Issue 060)。

## Decision

- **`state/transaction.py`を全mutation経路の唯一のcommit順序境界とする**。
  `project_lock()`/`commit_state_diff()`/`classify_recovery_state()`を提供し、
  driver commit phaseと`session/review.py`の重複を解消する。
- 1.0前に行うのは: transaction.py新設+driver/review統合、settings書込lock統合、
  auto-run coordinatorのlock統合+`web/auto_run.py`抽出(同じ行を触るためのbundle)のみ。
- import cycle 1(default_registryのagents側移設)・cycle 2(safety/types.py抽出)、
  state_manager分割、web/service残り分割は**post-1.0へ計測付き延期**
  (CIでcycle数・行数を観測、cycle 2を優先)。web/page.pyはrewrite非候補(ADR-0007/Issue 058)。

## Consequences

- refactorそれ自体は1.0の価値としない。1.0前の構造変更はADR-0008実装に必要な範囲に限定される。
- 純粋な移動はbehavior-preservingとし、既存全test緑+GitNexus impact確認を合否基準とする。
- post-1.0延期分は計測が可視化するため「暗黙の放置」にならない。
