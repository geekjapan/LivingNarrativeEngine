## add-random-engine — Grill残課題 (20260703)

### Q1. meta.yaml の rng 消費数フィールドの正式キー名とその整合性
- **対象**: `openspec/changes/add-random-engine/specs/random-engine/spec.md`(Requirement: Roll id の採番と RNG 状態の再構築)、`openspec/changes/add-turn-pipeline/specs/turn-pipeline/spec.md` 41-45行(Requirement: meta.yaml の内容)、`openspec/changes/add-session-autonomy/specs/session-autonomy/spec.md` 119行(resume 時の消費済み draw 数集計)
- **なぜ重要**: add-random-engine 側は「そのターンで消費した draw 回数を問い合わせ可能にする API」までしか責務を持たない(本 grill で自己解決済み。実際の `meta.yaml` 書き込みは turn-pipeline の責務と明記した)。一方 turn-pipeline 側の要件文は「rng sequence 番号」(41行、複数形が示唆する範囲/リスト風の表現)と Scenario の「rng sequence 消費数」(45行、カウント)という2通りの表現が同一フィールドを指しており、YAML 上の正式キー名(例: `rng_draws_consumed` か `rng_sequence_count` か等)がどちらの仕様にも書かれていない。session-autonomy は resume 時にこのフィールドを「各 `turn_NNNN/meta.yaml` の rng 消費数の累積」として合算する前提なので、3つの capability が同じキー名・同じ意味(ターン単位のカウントであり、通番範囲ではない)を共有できていないと resume の実装が壊れる。
- **自己調査**: spec-foundation §6(該当箇所)、turn-pipeline/spec.md 全文、session-autonomy/spec.md の resume 要件を確認したが、いずれも YAML キー名を明示しておらず、turn-pipeline 自身の要件文とシナリオの間で表現が割れている。add-random-engine のファイルのみを編集する制約下では、参照先である turn-pipeline の文言を直接統一できない。
- **検討した選択肢**: A) turn-pipeline の要件文を「rng sequence 番号」から「rng 消費数(カウント)」に統一し、正式キー名(例: `rng_draws_consumed`)を明記する / B) 各 capability が独自に解釈しても実質的に同じ値になる(範囲でも件数として読み替え可能)ため、現状のまま実装時にキー名を1つ決めて揃えれば足りるとみなす
- **推奨案**: A。実装フェーズで3つの capability の開発者が別々にキー名を決めると resume ロジックが静かに壊れるため、turn-pipeline 側の文言修正(範囲表現の削除、正式キー名の明記)を推奨する。
- **不足インプット**: turn-pipeline の要件文を修正してよいか、正式キー名をどう決めるか(ユーザー確認が必要)。
- **Status**: Resolved — D111: 正式キー名 `rng_draws_consumed`(ターン単位カウント)を meta.yaml 必須フィールドとして確定 (docs/spec-foundation.md §6, openspec/changes/add-turn-pipeline/)

### Q2. 失敗したターンの再試行時に rolls.yaml へ新旧レコードが混在する可能性
- **対象**: `openspec/changes/add-random-engine/specs/random-engine/spec.md`(Requirement: Roll ログの永続化)、`openspec/changes/add-turn-pipeline/specs/turn-pipeline/spec.md` 33-38行(失敗時の部分artifact永続化)・58-59行(次ターン番号の決定)
- **なぜ重要**: turn-pipeline は「次に実行するターン番号 = 最後に applied されたターン番号 + 1」と定めており、`failed` になったターンは applied ではないため、同じ `turn_NNNN` を再試行する際に番号が再利用されうる。その場合、失敗した1回目の試行が Resolve フェーズまで進んで `rolls.yaml` に一部 roll を書き込んでいた(「失敗時も必ず途中まで保存する」要件)なら、2回目の試行で新たに実行される roll がその同じ `rolls.yaml` に追記され、1回目(無効)と2回目(有効)の roll レコードが同一ファイル内で区別できないまま混在する。random-engine 自身の契約(roll id はグローバルに一意・追記のみ・上書きしない)はどちらの場合も守られるため random-engine 単体の実装は破綻しないが、`rolls.yaml` を読む側(narration/checker/exporter 等)が「そのターンの有効な roll 集合」をどう判定するかが未定義になる。
- **自己調査**: turn-pipeline/spec.md の失敗時永続化要件・次ターン番号決定要件を確認したが、同一 `turn_NNNN` の再試行時に artifact ディレクトリを新規作成するのか、既存ディレクトリに追記し続けるのかは明記されていない。add-random-engine 側だけでは「1ターンの中で試行(attempt)が複数回起こりうるかどうか」を決定できず、これは turn-pipeline の artifact 管理方針に依存する。
- **検討した選択肢**: A) turn-pipeline が失敗したターンを再試行する際は `turn_NNNN` ディレクトリを丸ごと作り直す(古い部分artifactは別途アーカイブするか破棄する)/ B) 同一ディレクトリに attempt 番号を付与したサブディレクトリ(例: `turn_0005/attempt_2/`)を切る / C) 現状のまま同一 `rolls.yaml` に追記させ、無効な roll を判別する手段(例: そのターンが最終的に `failed` のままアーカイブされた場合のみ古いレコードとして扱う)を別途定義する
- **推奨案**: B。turn-pipeline 側で attempt 単位のサブディレクトリを切れば、random-engine の「追記のみ・上書きしない」契約と衝突せずに新旧を明確に分離できる。ただし判断は turn-pipeline の設計範囲であり、本 change では決定できない。
- **不足インプット**: turn-pipeline が同一ターン番号の再試行をどう artifact 上で扱うか(ユーザー確認および turn-pipeline 側との調整が必要)。
- **Status**: Resolved — D112: 再試行/rerun は旧 artifact を `turn_NNNN_discarded_<n>` へ退避、rolls.yaml の新旧混在は発生しない (docs/spec-foundation.md §6, openspec/changes/add-turn-pipeline/)
