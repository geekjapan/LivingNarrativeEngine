## Context

企画書 §8/§9 は user mode と autonomy level を独立した軸として提示している。両者は組み合わせ次第で意味が矛盾しうる(例: 介入権限のない `watcher` に毎ターン確認を強制する `manual`)。また、GM レビューゲート・停止条件・resume・auto ループは全て「ターンパイプラインの Check→Commit 境界」という同じ地点を扱う関連機構であり、まとめて1 capability として設計する方が、artifact 契約(review.yaml・meta.yaml)を一貫させやすい。

## Goals

- user_mode / autonomy_level を検証可能な明示的モデルとして定義し、矛盾する組み合わせを黙って通さない。
- 停止条件の判定をレベルごとに一貫したルールで適用し、god mode(直接編集権限)と god level(ガードレール解除)という2つの異なる概念を混同しない。
- resume がワークスペースのファイルのみから完全に状態を復元できることを保証する(外部の実行時メモリに依存しない)。

## Non-Goals

- ブランチ管理 UX、介入サジェスト内容の生成、Web UI(proposal.md の Non-Goals を参照)。

## Decisions

### D1: mode/level の保存場所と CLI override の扱い

`project.yaml` の `user_mode` / `autonomy_level` フィールド(spec-foundation §5 で既に規定)を永続的な既定値として扱う。`run` / `resume` / `turn` 系 CLI コマンドの `--mode` / `--autonomy` フラグは、そのプロセス実行に限定したセッションローカルな override として適用し、`project.yaml` へは書き戻さない。override の使用有無と実際に使われた値は、各ターンの `meta.yaml` に記録する(監査可能性のため)。

**代替案**: override を毎回 `project.yaml` に永続化する案は、ユーザーが一時的にモードを変えて観察したいだけのケース(例: デバッグのため1回だけ `god` で実行)で不本意な設定変更を招くため不採用。永続変更が必要な場合は明示的な `config set` コマンド(cli capability の責務)を使う。

### D2: 停止条件の評価地点

停止条件の評価は Check フェーズ完了後・Commit フェーズ実行前(state diff 適用前)に行う。これは spec-foundation §6 のフェーズ順序と整合し、`checker_error` を含む全ての条件を Commit 前にまとめて判定できる。ただし `scene_end` と `target_turn_count_reached` はターンの結果(Commit 後の状態)に依存しうるため、Commit 実行後にも軽量な2回目の評価(シーン遷移検知・ターンカウンタ確認)を行う。

**代替案**: 全条件を Commit 後にのみ評価する案は、`checker_error` によって「エラーを含む state diff がすでに適用済み」という状態を生みかねず、spec-foundation §6 の「決して黙って握り潰さない」という不変条件に反するため不採用。

### D3: God Mode(user_mode)と god レベル(autonomy_level)の分離

`god` モードは「何を編集できるか」(権限マトリクスの対象)であり、`god` レベルは「自律進行がどこまで止まらないか」(停止条件の適用有無)である。両者は別々に選択可能(例: `god` モードだが `manual` レベルで慎重に1手ずつ確認しながら世界を編集する、という組み合わせも有効)。God Mode の diff/ログ強制(D107)は user_mode の性質であり、autonomy_level の値に関わらず常に適用される。

### D4: Rerun の乱数セマンティクス

既定は「新規シーケンス消費」とする。GM が rerun を選ぶ主な動機は「別の結果を見たい」であり、同一シードでの再実行は入力(intervention)を変えない限り同一結果を再現するだけで無意味だからである。同一シード再現(`--replay-same-seed`)は、決定論のデバッグ・回帰確認という別ユースケース向けの明示的オプションとして用意する。

### D5: Player Character 入力のルーティング

`player_character` モードのユーザー入力は、Intervention Interpreter を経由する自由文介入としてではなく、Intervene フェーズから直接 Act フェーズ相当の出力(`agent_io/<char_id>.yaml`)へ書き込む専用経路を取る。これにより、当該キャラクターの Character Agent(LLM 呼び出し)をそのターンだけスキップでき、トークン消費を避けつつ「ユーザー=そのキャラクター」という一貫性を保てる。他のキャラクターへの `character_directive`(自分以外へのディレクティブ)は権限マトリクス上そもそも許可されない。

## Risks & Trade-offs

- [Risk] mode×level 正規化ルールが将来モード追加時に硬直的になる可能性。 → Mitigation: 正規化ルールを「条件式のリスト」として実装し、新モード追加時は該当条件式を1件追加するだけで済む構造にする(ハードコードされた5×6マトリクス全体を書き直さない)。
- [Risk] 停止条件評価をCommit前後2箇所に分割することで実装が複雑化する。 → Mitigation: 評価ロジック自体は単一の関数にまとめ、呼び出しタイミング(pre-commit / post-commit)だけをパイプライン側で切り替える。
- [Risk] rerun の「新規シーケンス消費」既定が、ユーザーの直感(seedを固定したのに毎回結果が違う)に反する可能性。 → Mitigation: rerun 実行時のメッセージで乱数消費セマンティクスを明示し、`--replay-same-seed` の存在を案内する。

## Open Questions

- `major_canon_change` の「重大」判定基準(変更件数か、canon の重要度タグか)は state-model / consistency-checks capability 側の定義待ちであり、本 change では「重大度が閾値を超える」という抽象条件として扱う。閾値の具体的な算出方法は将来 change で確定する。
- watch レベルでの「介入候補の提示」の既定オフを、プロジェクト設定で明示的にオンにできるようにするかは cli capability 側の UX 決定に委ねる。
