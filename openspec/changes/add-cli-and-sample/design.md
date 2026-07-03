# Design: add-cli-and-sample

## Context

先行する全 change(project-foundation 〜 session-autonomy)により、状態モデル・乱数・LLM provider・turn pipeline・agent・intervention・自律進行の判断ロジックが揃う。本 change はこれらを人間が実際に操作できる CLI として束ね、企画書 §21.4 の MVP 成功条件(サンプル世界を10〜20ターン破綻せず進められる)をサンプル世界「霧の駅」+ 20ターン smoke test(範囲の上限を実証)で実証する、第1バッチ最後の change である。新規のドメインロジックはほぼ持たず、既存 capability の配線とデータ(サンプル世界)が中心となる。

## Goals

- 企画書 §29 のユーザーフローをそのまま実行できる CLI を提供する。
- CLI は薄いレイヤーに留め、既存 capability のロジックを重複実装しない。
- CI・スクリプトから完全に非対話で全コマンドを実行できるようにする。
- 「霧の駅」を、隠し真実が実際に leak checker の検出対象になるよう設計し、consistency-checks の実効性を証明する。
- 20ターン smoke test を、企画書 §21.4 の全成功条件(10〜20ターンという範囲の上限を含む)に1:1で対応する回帰テストとして固定する。

## Non-Goals

- Web UI・TUI・シェル補完の作り込み(spec-foundation D101、proposal.md Non-Goals 参照)。
- 新しい判断ロジック(停止条件・permission・diff計算等)の実装。これらは既存 capability に委譲する。
- `mist_station`/`minimal` 以外のテンプレート追加。

## Decisions

### D1: CLI は engine 層の公開 API を呼び出すだけの薄いレイヤーとする

typer の各コマンド関数は、`living_narrative` の各 capability パッケージ(`pipeline`・`intervention`・`session_autonomy` 等)が公開する関数/クラスを呼び出し、その戻り値を標準出力向けに整形するだけの実装とする。state diff の計算・可視性判定・停止条件の判断といったロジックは CLI モジュール内に一切書かない。

- 根拠: 将来の `web` コマンド追加(第2バッチ)時に同じ engine API を再利用できる。CLI 層の変更が既存 capability のテスト済みロジックに影響しないようにする。
- 代替案: CLI 内でパイプライン呼び出しを直接組み立てる — 実装は速いが、Web UI 追加時にロジックの二重実装が発生するため不採用。

### D2: 非対話フラグは「対話プロンプトと1:1対応する明示フラグ」方式とする

`review` コマンドの `--decision accept_all|reject_all|partial|edit|rerun_turn`(session-autonomy の `review.yaml` decision 正準値と1:1)のように、対話プロンプトの各選択肢に対応する CLI フラグを用意する。`--decision rerun_turn` は追加で任意フラグ `--replay-same-seed` を受け付け、session-autonomy の同一シード再現セマンティクス(Requirement「Rerun の乱数消費セマンティクス」)を呼び出す。`rerun_turn` を伴わない `--replay-same-seed` はエラーとする。TTY が存在しない、かつ必要なフラグが不足している場合は、プロンプト表示を試みず即座にエラー終了する。

- 根拠: CI/スクリプトでの安定動作(ブロッキング防止)を保証する。フラグと対話プロンプトの選択肢を1:1にすることで、ドキュメント化・テストが容易になる。
- 代替案: `--yes` のような一括同意フラグのみを用意する — partial/edit のような細かい決定を表現できず、企画書 §10.10 の要求(accept all / reject all / edit / apply partially)を満たせないため不採用(単純な `accept`/`reject` のみのケースでは今後 `--yes` 相当のショートハンドを追加する余地は残す)。

### D3: サンプル世界「霧の駅」は、隠し真実ごとに検出可能な接点を持たせて設計する

`gm_vault` の隠し真実3件(封印施設の存在・カイの部分的知識・ミラの正体)は、それぞれ最低1体のキャラクターの `knowledge`/`secrets`/`private_mind` に関連付け、シーンやキャラクター行動を通じて narration に漏れうる経路を持たせる。具体的には、カイの `knowledge.believes` に封印施設への部分的な気づきを、ミラの `secrets` に正体を、双方の `private_mind` に対応する内心を配置する。

- 根拠: leak checker が「検出対象が存在しない状態でエラーが出ないだけ」のテストにならないようにするため。隠し真実が narration の入力候補になりうる状態を作ることで、20ターン smoke test の「error 級リーク無し」検証に意味を持たせる。
- 代替案: 隠し真実をどのキャラクターにも関連付けない(GM Vault にのみ存在)— リーク検出の検証対象が形式的になり、smoke test が leak checker の実効性を証明できないため不採用。

### D4: 20ターン smoke test は mock provider + 固定 seed + スクリプト化された介入で完全決定的にする

smoke test は20ターン(企画書§21.4 の MVP 成功条件の範囲上限)を対象とし、`random_seed` を固定し、mock provider の応答を各ターンで決定的に固定した上で、ターン3・6の介入は自由文ではなく構造化直接入力(`--type` フラグ相当、`intervention` capability の直接入力パス)で与える。これにより、LLM interpreter の解釈揺らぎを smoke test の非決定要素から排除する。

- 根拠: spec-foundation §7/§8 の「同一 seed + 同一介入列 + mock provider ⇒ 完全再現」契約に厳密に従う。自由文 + mock interpreter でも決定的だが、直接入力パスの方がテストの意図(「この介入が反映されること」)を明確に表現できる。
- 代替案: 自由文介入を smoke test で使う — mock provider の応答が決定的であれば理論上問題ないが、interpreter の解釈結果を smoke test のアサーション対象にすると、interpreter 実装の細部変更で smoke test が壊れやすくなるため不採用。

## Risks & Trade-offs

- [Risk] `review` の非対話フラグ体系が過度に複雑になり、実装・ドキュメントの負担が増える。
  → Mitigation: 第1バッチでは `accept_all`/`reject_all`/`rerun_turn` を単純フラグ、`partial`/`edit` のみインデックス指定・パッチファイルという最小限の追加引数に留める(D2)。`partial` のインデックス選択は session-autonomy の GM レビューゲート契約(change のインデックス集合)にそのまま従う。
- [Risk] サンプル世界の隠し真実がシナリオ上一度も参照されず、leak checker のテストが形骸化する。
  → Mitigation: D3 の設計方針を tasks.md のサンプル世界作成タスクに明記し、smoke test 側で各隠し真実に関連するキャラクター行動が最低1ターンは発生することをレビュー観点に含める。
- [Risk] CLI が薄いレイヤーであるという制約が、実装中になし崩し的に破られる(便利さ優先でロジックを CLI に書いてしまう)。
  → Mitigation: D1 をコードレビュー観点として明記し、CLI モジュールに engine API 呼び出し以外の分岐ロジックが増えていないかを tasks.md のテストタスクで確認する。

## Open Questions

- `review --decision edit --patch <file>` のパッチファイル形式(state diff スキーマそのものか、diff-of-diff 形式か)の詳細は実装時に確定する。20ターン smoke test の MVP 成功条件(4)は「review or auto-apply を経て適用」という選言であり、auto-apply のみで満たせるため、`review` の各 decision フラグ(`partial`/`edit`/`rerun_turn` を含む)を smoke test 自体で網羅する必要はなく、これは smoke test をブロックしない。decision フラグの網羅的検証は section 3 の pytest(3.9)の責務とする。
- `export replay` にターン範囲指定(`--from-turn`/`--to-turn`)を追加するかは、企画書に明記が無いため本 change では対象外とし、必要になった時点で別 change として提案する。
