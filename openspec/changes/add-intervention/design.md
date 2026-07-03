## Context

Intervention は企画書の核心原則(§5.2「ユーザー指示を第一級オブジェクトにする」)を具体化する capability であり、`add-agent-runtime` が提供する実行主体(Character Agent / World Simulator / Narrator / State Manager)と `add-llm-provider` の構造化出力を橋渡しする。15種の介入タイプ(企画書 §10.7)全てを第1バッチで作り込むとスコープが肥大化する(企画書 §24.6 のリスク)ため、スキーマと権限モデルは15種全てを扱いつつ、実行ロジックは9種に絞る設計とする。

## Goals

- ユーザーの意図(自由文・構造化入力)を一切黙って捨てず、必ず型付き Intervention として保存する。
- 15種すべてをスキーマ・履歴・permission の対象としつつ、専用実行ロジックが無い型を明示的に区別し、将来の change で安全に追加できる形にする。
- state 変更を伴う介入(canon_edit/hidden_truth_edit)は D107 の diff 経由原則を一切迂回しない。
- 権限判定をコードの if 分岐に散らさず、テスト・レビューが容易なデータとして持つ。

## Non-Goals

- 6種の未ハンドルタイプに対する具体的な状態変更ロジックの設計(将来 change のスコープ)。
- Interpreter の分類精度そのものの最適化(プロンプトエンジニアリングの詳細はタスクレベルの実装判断とする)。
- assist モードでの「解釈結果をユーザーに見せて確認を取る」UI/CLI フロー(session-autonomy / cli の責務)。

## Decisions

### D1: Interpreter は Intervention の「リスト」を返し、未分類テキストは scene_directive にフォールバックする

- 決定: Interpreter の response_schema は `interventions: list[Intervention]` + `confidence: float` + `interpretation_summary: str` とする。自由文のうち既知 type に明確に分類できなかった部分は、破棄せず `type: scene_directive` として `content` にそのまま残す。
- 理由: 企画書 §5.2 の核心原則(ユーザー指示は消費して消してはならない)を字面通りに守る最も単純な方法。単一の Intervention に固定すると、複数意図を含む自由文(§7.2 の例)を表現できない。
- 代替案: 「最も確信度の高い1件のみを返す」設計 — シンプルだが、ユーザー指示の一部が黙って消える(企画書の核心原則に反する)ため不採用。

### D2: Permission table はデータ(辞書)として持ち、判定は純粋関数1本に集約する

- 決定: `type -> set[user_mode]` の辞書をモジュールレベルの定数として持ち、`check_permission(type, user_mode) -> Ok | Rejection` という1つの純粋関数で判定する。15種全ての行を明示的に埋める(欠落した type がある場合はテストで検出できるようにする)。
- 理由: D108(レジストリ辞書、plugin loader は作らない)と同じ思想。if/elif の分岐に権限ロジックを混ぜると、type が増えるたびに分岐漏れのリスクが生じる。データ駆動なら permission table を一覧すればレビューだけで正しさを確認できる。
- 代替案: user_mode に序数(ordinal)を割り当て「type ごとの最小 ordinal」で判定する設計 — しかし企画書 §8 の6モードは厳密な線形順序を持たない(例: `author` と `player_character` はどちらが「上位」か定義できない)。誤った序数関係を捏造するより、type ごとに許可集合を明示するほうが安全。

### D3: canon_edit / hidden_truth_edit は State Manager の diff 経路のみを通る

- 決定: `canon_edit` / `hidden_truth_edit` intervention は、intervention モジュールが直接 `canon.yaml` / `gm_vault.yaml` を書き換えることはせず、`source_event`(または intervention id を参照する同等のフィールド)を持つ state diff エントリを生成し、`add-state-model` の StateDiff 適用エンジンに渡すことで反映する。
- 理由: D107(state 変更は全て diff 経由。God Mode も diff を発行する)を intervention capability でも一貫させる。これにより canon_edit/hidden_truth_edit も他の state 変更と同様に rollback・review・監査の対象になる。
- 代替案: God Mode 由来の変更のみ直接書き込みを許す特例パス — D107 の例外を作ることになり、rollback・監査の一貫性が壊れるため不採用。

### D4: reveal_control はフラグ付与のみ行い、実際の昇格/抑制は Commit フェーズで解決する

- 決定: `reveal_control` intervention は該当ターンの間、対象事実に `must-not-reveal` / `reveal-now` のマークを付けるだけの中間データとして扱い、実際の Reader State 昇格判定は spec-foundation §6 の Commit フェーズ(state diff 確定のタイミング)で行う。
- 理由: reveal 判定は他の候補生成(Simulate/Act/Resolve)の後、最終的にどの事実が reader 可視イベントとして残るかが確定してから行う必要がある。Intervene フェーズの時点では対象事実がまだ候補にすら含まれていない可能性がある。
- トレードオフ: `reveal_control` の効果が「即座に」見えず、ターン内の他フェーズの結果に依存する。これは仕様として明示し(本 spec の reveal_control 要件)、テストで Commit 時点の挙動として検証する。

## Risks & Trade-offs

- [Risk] Interpreter が自由文を誤分類する(例: character_directive を world_directive と誤認)。→ Mitigation: confidence を必須フィールドとして出力させ、低 confidence 時の扱い(assist モードでの確認要求等)は `session-autonomy` に委ねる。本 change はデータを提供するのみ。
- [Risk] Permission table の user_mode 列挙が `session-autonomy` 側の実際のモード定義とずれる可能性。→ Mitigation: user_mode の正本は spec-foundation §5 が参照する `project.yaml` の `user_mode` フィールド(企画書 §8 準拠)であり、intervention capability は独自定義を持たず参照するのみ。
- [Risk] 6種の未ハンドルタイプが「何もしない」ことに気づかれず、ユーザーが機能していると誤解する。→ Mitigation: 本 spec の「Type 別ハンドリング状況の明示」要件により、システム内部でハンドリング状況を明示可能にする。ユーザー向けの警告表示自体は cli capability の責務。
- [Risk] `interventions.yaml` がセッション長期化で肥大化する。→ Mitigation: 第1バッチのターン規模(数十〜百ターン)では許容範囲(spec-foundation の random-engine 設計と同様の判断)。圧縮・アーカイブは対象外。

## Open Questions

- 低 confidence な Interpreter 出力に対する自動停止しきい値は未確定(`session-autonomy` の stop condition 設計で決定する。本 change をブロックしない)。
- 6種の未ハンドルタイプのうち、どれを次のバッチで優先実装するかは未確定(ユーザー確認事項、本 change をブロックしない)。
