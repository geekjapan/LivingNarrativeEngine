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

### D6: 破棄された rerun artifact の保持方式と乱数累積数の再構築

`turn_NNNN_discarded_<attempt連番>`(例: `turn_0018_discarded_1`)という退避先ディレクトリ命名は、`rerun_turn`(本 capability)と failed ターンの再試行(add-turn-pipeline)の両方が従う共有契約であり、spec-foundation §6(D112)がその正本である。add-turn-pipeline はこの契約を実現するユーティリティ(次ターン番号の決定、discarded ディレクトリへの退避、`meta.yaml` のステータス更新。turn-pipeline grill Q4 裁定、design.md D8 参照)を公開し、本 capability はそれらを直接呼び出す。`rerun_turn` によって破棄される旧ターン artifact は `turn_NNNN` ディレクトリ名を再利用せず `turn_NNNN_discarded_<attempt連番>` へリネームしてから保持する。新しい実行結果のみが `turn_NNNN` を名乗る。これにより、resume・次ターン番号決定(add-turn-pipeline「次ターン番号の決定と未解決ターンによるブロック」)は常に `turn_NNNN` ディレクトリのみを走査すればよく、破棄済み attempt を誤って「最後に applied されたターン」として拾うことがない。

`rerun_turn` はさらに、破棄対象ターンに属する `interventions.yaml`(add-intervention 定義)の該当エントリへ `superseded_by_rerun: true` を付与しなければならない(SHALL)。add-intervention の「Intervention 履歴インデックス」要件は、rerun による事後の追記・訂正方法を「session-autonomy との調整事項」として明示的に対象外としており、本 D6 がその調整を確定する。このフラグはエントリの source reference が新しい attempt の結果を指さなくなったことを示す監査マーカーであり、エントリ自体は削除・上書きしない。

一方、add-random-engine の RNG 状態は `random_seed` と「これまでに消費した draw 数」のみから再構築される単調増加カウンタであり、rerun の既定(新規シーケンス消費)は破棄された attempt が消費した draw を巻き戻さない(Requirement「Rerun の乱数消費セマンティクス」)。したがって resume が計算する「乱数エンジンの消費済み draw 数」の累積は、`turn_NNNN`(現存する最新 attempt)だけでなく、同一ターン番号に対して破棄された全 `turn_NNNN_discarded_*` の rng 消費数も合算しなければならない(SHALL)。`--replay-same-seed` 指定時に巻き戻す「当該ターン開始前の乱数消費数」も同じ規則で、対象ターンより前の全ターン(discarded 分を含む)の累積で算出する。

**代替案**: 破棄 attempt を削除せず `turn_NNNN` のまま上書きする案は、監査可能性の要件(旧 artifact 保持)と直接矛盾するため不採用。破棄 attempt を rng 累積計算から除外する案は、rerun の既定「新規シーケンス消費」の前提(旧 attempt の draw は巻き戻さない)と矛盾し、resume 後の draw 結果が非中断実行と一致しなくなるため不採用。共有契約を本 capability 側で独自に再定義する案(命名規則を session-autonomy 固有のものとして扱う)は、failed ターン再試行(add-turn-pipeline)との命名衝突・二重実装を招くため不採用。

### D7: intervention の Role Permission Hook との権限データの権威関係

`add-intervention` の Role Permission Hook(intervention type ごとの許可 user_mode 集合)は、DAG 上 `add-session-autonomy` より前に定義されるため、少なくとも `canon_edit`/`hidden_truth_edit` を `full_gm`/`god` のみへロックする最小限のデータのみを持つ(add-intervention 側の SHALL は「少なくとも」の範囲に留まる)。本 capability の権限マトリクス(Requirement「ユーザーモードの権限マトリクス」)は、全6モード×全15 type の完全な許可関係を定義する上位の正本であり(spec-foundation D114)、intervention の Role Permission Hook が持つ最小ロック(2 type分)と矛盾しない値を持つ(本 change の時点で確認済み: canon_edit/hidden_truth_edit は本マトリクス上も full_gm/god のみ許可)。権限判定の実施点は intervention capability の Interpreter が行う生成時チェック(D114 のいう「プラガブル判定」フック)一箇所のみであり、本マトリクスはそのフックへ供給されるデータにすぎない。本 capability(session-autonomy)は、Interpreter が既に生成した intervention を受け取った後で権限マトリクスを再評価し二重に却下する経路を持たない(SHALL NOT。二重の却下判定点は作らない)。intervention 側の Role Permission Hook データを実装時に本 capability の権限マトリクスから機械的に導出するか、独立したハードコードのまま残置するかは実装判断とするが、値の不一致は許容しない。

### D8: GM レビューゲート事後操作の実行境界(turn-pipeline の外側)

`partial`/`edit`/`rerun_turn` はターンの実行そのものではなく、既に `pending_review`/`stopped_for_review` として確定した既存ターンに対する事後操作である。add-turn-pipeline の design.md D4 が明示する恒久インターフェース(Commit フェーズが「apply するか否かの bool」を受け取るのみ)を変更しない移行方針を尊重し、これらの事後操作は turn-pipeline のフェーズ実行を経由せず、本 capability が (1) state-model の diff 適用 API(partial apply・rollback 等、既存)を直接呼び出し、(2) add-turn-pipeline が公開する事後操作向けユーティリティ(次ターン番号の決定ロジック、`turn_NNNN_discarded_<n>` への退避処理、`meta.yaml` のステータス更新。design.md D6 参照)を直接呼び出す、という2系統の直接呼び出しのみで完結させる(turn-pipeline grill Q4 の裁定案Bを採用)。`review.yaml` の書き込みも本 capability 自身が担当する。ただし `rerun_turn` の「事後操作」に該当するのは退避処理と決定記録までであり、退避後に行う新しい attempt の実行は事後操作ではなく通常のターン実行として TurnPipeline の8フェーズ全体を経由する(events・narration・checks・state diff は本 capability が再生成するのではなく、パイプラインの再実行によって生成される)。

**代替案**: add-turn-pipeline に専用の事後操作 API(例: `finalize_pending_turn`)を新設させる案は、D4 の「インターフェースを変えない」という移行方針と衝突し、turn-pipeline の責務を「1ターンを1回、順序どおり実行する」ことから逸脱させるため不採用。

## Risks & Trade-offs

- [Risk] mode×level 正規化ルールが将来モード追加時に硬直的になる可能性。 → Mitigation: 正規化ルールを「条件式のリスト」として実装し、新モード追加時は該当条件式を1件追加するだけで済む構造にする(ハードコードされた5×6マトリクス全体を書き直さない)。
- [Risk] 停止条件評価をCommit前後2箇所に分割することで実装が複雑化する。 → Mitigation: 評価ロジック自体は単一の関数にまとめ、呼び出しタイミング(pre-commit / post-commit)だけをパイプライン側で切り替える。
- [Risk] rerun の「新規シーケンス消費」既定が、ユーザーの直感(seedを固定したのに毎回結果が違う)に反する可能性。 → Mitigation: rerun 実行時のメッセージで乱数消費セマンティクスを明示し、`--replay-same-seed` の存在を案内する。

## Open Questions

- `major_canon_change` の「重大」判定基準(変更件数か、canon の重要度タグか)は state-model / consistency-checks capability 側の定義待ちであり、本 change では「重大度が閾値を超える」という抽象条件として扱う。閾値の具体的な算出方法は将来 change で確定する。
- ~~`character_death`/`heavy_roll_failure`/`scene_end` の判定に必要な具体的フィールドが他 capability 側で未確定~~ → **Resolved(spec-foundation D123)**: `character_death` は state diff 中の `CharacterState.status` の `dead` への遷移、`heavy_roll_failure` は `rolls.yaml` 中の roll の `severity: critical` かつ失敗 `outcome`(severity は Conflict Resolver が明示指定、add-agent-runtime D6。critical でも成功した roll では停止しない)、`scene_end` は state diff 中の `SceneState.status` の `ended` への遷移で機械的に評価する。詳細は spec.md「停止条件の判定とレベル別適用」Requirement を参照。フィールド自体のスキーマ定義は add-state-model / add-random-engine の責務であり、本 change は評価ロジックのみを実装する。
- watch レベルでの「介入候補の提示」の既定オフを、プロジェクト設定で明示的にオンにできるようにするかは cli capability 側の UX 決定に委ねる。
