## Context

Intervention は企画書の核心原則(§5.2「ユーザー指示を第一級オブジェクトにする」)を具体化する capability であり、`add-agent-runtime` が提供する実行主体(Character Agent / World Simulator / Narrator / State Manager)と `add-llm-provider` の構造化出力を橋渡しする。15種の介入タイプ(企画書 §10.7)全てを第1バッチで作り込むとスコープが肥大化する(企画書 §24.6 のリスク)ため、スキーマと権限モデルは15種全てを扱いつつ、本 change 内で専用実行ロジックを実装するのは9種に絞り、`stop_condition` は `session-autonomy` capability への明示的な消費先として扱う設計とする(D119)。

## Goals

- ユーザーの意図(自由文・構造化入力)を一切黙って捨てず、必ず型付き Intervention として保存する。
- 15種すべてをスキーマ・履歴・permission の対象としつつ、専用実行ロジックが無い型を明示的に区別し、将来の change で安全に追加できる形にする。
- state 変更を伴う介入(canon_edit/hidden_truth_edit)は D107 の diff 経由原則を一切迂回しない。
- 権限判定をコードの if 分岐に散らさず、テスト・レビューが容易なデータとして持つ。

## Non-Goals

- 残る5種の未ハンドルタイプに対する具体的な状態変更ロジックの設計、および `stop_condition` の停止条件評価ロジック自体の設計(いずれも将来 change / `session-autonomy` のスコープ)。
- Interpreter の分類精度そのものの最適化(プロンプトエンジニアリングの詳細はタスクレベルの実装判断とする)。
- assist モードでの「解釈結果をユーザーに見せて確認を取る」UI/CLI フロー(session-autonomy / cli の責務)。

## Decisions

### D1: Interpreter は Intervention の「リスト」を返し、未分類テキストは scene_directive にフォールバックする

- 決定: Interpreter の response_schema は `interventions: list[Intervention]` + `confidence: float` + `interpretation_summary: str` とする。llm-provider の呼び出しは binding key `interpreter`(spec-foundation D122)で解決したプロファイルを用いる。自由文のうち既知 type に明確に分類できなかった部分は、破棄せず `type: scene_directive` として `content` にそのまま残す。ただし LLM に生成させるのは各 `interventions[]` 要素の `type`/`target`/`content`/`constraints`/`visibility` のみであり、`id`(spec-foundation §3 の project 内一意通番)・`turn`・`user_role` は LLM 出力に含めない。これらはターン実行コンテキストからパイプライン統合層が確定値を補完したうえで、正規の `Intervention` モデルとして検証・確定する(直接入力パスも同一規則に従う。§構造化直接入力パス参照)。
- 理由: 企画書 §5.2 の核心原則(ユーザー指示は消費して消してはならない)を字面通りに守る最も単純な方法。単一の Intervention に固定すると、複数意図を含む自由文(§7.2 の例)を表現できない。id/turn/user_role を LLM に生成させないのは、project 内一意な連番 id を LLM が正しく採番できず、また turn・user_role は呼び出し時点で既知であり LLM に推測させる理由がないため。
- 代替案: 「最も確信度の高い1件のみを返す」設計 — シンプルだが、ユーザー指示の一部が黙って消える(企画書の核心原則に反する)ため不採用。

### D2: Permission 判定は普遍的不変条件のみをハードコードし、それ以外はプラガブルな permission table に委ねる

- 決定: 権限判定は `check_permission(type, user_mode, permission_table) -> Ok | Rejection` という1つの純粋関数に集約する。`permission_table`(`type -> set[user_mode]`)はデータ注入される引数であり、intervention capability 自身がハードコードするのは D107 由来の普遍的不変条件(`canon_edit`/`hidden_truth_edit` は `full_gm`/`god` のみ許可)のみとする。それ以外の13種の type×user_mode 許可可否は外部(`session-autonomy` capability、企画書§8のモード定義起点)から供給される permission table に委ねる。`session-autonomy` が未配線の場合の既定 permission table は、上記不変条件を除き全許可(permissive)とする。本 change は15種×6モードの完全なマトリクスの正本を主張しない(D114、spec-foundation §9)。
- 理由: spec-foundation §9 D114 により、type×user_mode 権限マトリクスの正本は `session-autonomy` capability であると確定した。intervention capability が独自に全13行を固定してしまうと、`session-autonomy` 実装時に二重管理・値の食い違いが生じる(Grill Q1)。また spec-foundation §1.2 の DAG では `add-intervention` → `add-session-autonomy` の順であり、`add-intervention` は `add-session-autonomy` に依存できないため、判定関数をプラガブルにしてデータを外部注入可能にすることで、DAG 順序を守りつつ後段の `session-autonomy` が本来の制限を追加できる。判定ロジック自体を純粋関数1本に集約する方針(if/elif に分岐を混ぜない)は変更しない。
- 代替案: user_mode に序数(ordinal)を割り当て「type ごとの最小 ordinal」で判定する設計 — 企画書 §8 の6モードは厳密な線形順序を持たない(例: `author` と `player_character` はどちらが「上位」か定義できない)ため不採用。旧案(15種全ての行を intervention capability 自身が固定して埋める)— `session-autonomy` との二重管理・食い違いを招くため不採用(Grill Q1 推奨案 B)。

### D3: canon_edit / hidden_truth_edit は State Manager の diff 経路のみを通る

- 決定: `canon_edit` / `hidden_truth_edit` intervention は、intervention モジュールが直接 `canon.yaml` / `gm_vault.yaml` を書き換えることはせず、`source_event`(または intervention id を参照する同等のフィールド)を持つ state diff エントリを生成し、`add-state-model` の StateDiff 適用エンジンに渡すことで反映する。
- 理由: D107(state 変更は全て diff 経由。God Mode も diff を発行する)を intervention capability でも一貫させる。これにより canon_edit/hidden_truth_edit も他の state 変更と同様に rollback・review・監査の対象になる。
- 代替案: God Mode 由来の変更のみ直接書き込みを許す特例パス — D107 の例外を作ることになり、rollback・監査の一貫性が壊れるため不採用。

### D4: reveal_control はフラグ付与のみ行い、実際の昇格/抑制は BuildDiff スロットで解決する

- 決定: `reveal_control` intervention は該当ターンの間、対象事実に `must-not-reveal` / `reveal-now` のマークを付けるだけの中間データとして扱う。実際の Reader State 昇格判定の強制点は、spec-foundation §6 フェーズ8(Commit)内の **BuildDiff スロット**(agent-runtime の State Manager が実装、turn-pipeline がスロット契約を定義。D113)である。turn-pipeline 側に intervention 専用の Commit hook を新設する必要はない — BuildDiff は resolved events + interventions を入力に state diff 候補を生成する契約として既に定義されており、reveal_control の must-not-reveal 遵守は BuildDiff 契約に含まれる。intervention capability の責務は BuildDiff が参照する制約データ(must-not-reveal / reveal-now マーク)を生成することのみである。この効果は Narrator 制約としての伝達(Requirement「Type別ルーティング」)とは独立した第二の効果であり、両方が同時に成立しなければならない — Narrator 制約は生成される prose がその事実に言及しないようにするものであり、BuildDiff での昇格制御は `reader_state.yaml` という構造化データへの正式な追加/抑制を扱う。前者のみの実装では、prose は事実を明言しなくても `reader_state.yaml` に事実が記録されてしまい得るため要件を満たさない。機構としては、BuildDiff が生成する state diff 候補のうち target が `reader_state` かつ対象事実が当該ターンの `must-not-reveal` マークに一致する change を除外し、`reveal-now` マークが付いた GM Vault / Canon 上の事実については target `reader_state` の change を(`source_event` に当該 intervention id を付与して)BuildDiff の出力に追加することで実現する。
- 理由: reveal 判定は他の候補生成(Simulate/Act/Resolve)の後、最終的にどの事実が reader 可視イベントとして残るかが確定してから行う必要がある。BuildDiff は resolved events(Resolve フェーズの出力)を入力に取るため、この時点で対象事実が候補として揃っている。D113 により BuildDiff は agent-runtime の State Manager が実装するスロットとして turn-pipeline 契約に既に定義されており、intervention capability は独自の統合点を新設する必要がない(Grill Q2 推奨案 C を BuildDiff スロットという既存機構で実現)。
- トレードオフ: `reveal_control` の効果が「即座に」見えず、ターン内の他フェーズ(Resolve まで)の結果に依存する。これは仕様として明示し(本 spec の reveal_control 要件)、テストで BuildDiff 出力の挙動として検証する。intervention capability の責務は制約データの生成のみであり、BuildDiff 自体の実装は `add-agent-runtime`(State Manager)の責務である。

## Risks & Trade-offs

- [Risk] Interpreter が自由文を誤分類する(例: character_directive を world_directive と誤認)。→ Mitigation: confidence を必須フィールドとして出力させ、低 confidence 時の扱い(assist モードでの確認要求等)は `session-autonomy` に委ねる。本 change はデータを提供するのみ。
- [Risk] Permission table の user_mode 列挙が `session-autonomy` 側の実際のモード定義とずれる可能性。→ Mitigation: user_mode の正本は spec-foundation §5 が参照する `project.yaml` の `user_mode` フィールド(企画書 §8 準拠)であり、intervention capability は独自定義を持たず参照するのみ。
- [Risk] 残る5種の未ハンドルタイプが「何もしない」ことに気づかれず、ユーザーが機能していると誤解する。→ Mitigation: 本 spec の「Type 別ハンドリング状況の明示」要件により、システム内部でハンドリング状況を明示可能にする。ユーザー向けの警告表示自体は cli capability の責務。
- [Risk] `interventions.yaml` がセッション長期化で肥大化する。→ Mitigation: 第1バッチのターン規模(数十〜百ターン)では許容範囲(spec-foundation の random-engine 設計と同様の判断)。圧縮・アーカイブは対象外。

## Open Questions

- 低 confidence な Interpreter 出力に対する自動停止しきい値は未確定(`session-autonomy` の stop condition 設計で決定する。本 change をブロックしない)。
- 残る5種の未ハンドルタイプのうち、どれを次のバッチで優先実装するかは未確定(ユーザー確認事項、本 change をブロックしない)。
- `interventions.yaml` の `superseded_by_rerun` フラグは `session-autonomy` の rerun 操作が設定する(Requirement「Intervention 履歴インデックス」、D112)。具体的にどのタイミングで `session-autonomy` がこのフラグを更新するか(rerun_turn 実行と同期的に更新するか、次回 Commit 完了時にまとめて更新するか)の実装順序は本 change 単独では確定できない(cross-change の調整が必要、本 change をブロックしない)。
