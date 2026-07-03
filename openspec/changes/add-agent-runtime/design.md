# Design: add-agent-runtime

## Context

`add-turn-pipeline` は8フェーズ(Load/Intervene/Simulate/Act/Resolve/Narrate/Check/Commit)と turn artifact 契約のみを定義し、Simulate/Act/Resolve/Commit の各スロットには何もしない、または最小限のダミー実装が入っている。本 change は、この4スロットに実際の知能(Context Builder / Character Agent / World Simulator / Conflict Resolver / State Manager)を実装として差し込み、加えて Check フェーズの中身(checker フレームワーク・Leak Checker・Continuity Checker)を実装する。

情報スコープ(spec-foundation §4)は本プロダクトの核となる契約であり、これを守れないと「キャラクターが未公開情報を知っているように振る舞う」「読者に秘密が漏れる」という、企画書 §3.1 が名指しする既存 AI 小説生成の中心的な弱点をそのまま再現してしまう。したがって本 change の設計判断の大半は、スコープ遵守をテスト可能な形にどう落とし込むかに集中している。

## Goals

- LLM を一切呼ばずに、コンテキストスコープの不変条件を検証できるテストスイートを持つ。
- agent の入出力を全て型付きスキーマで表現し、llm-provider の構造化出力検証に載せる。
- 衝突解決の順序を決定的にし、mock provider + 固定 seed でのリグレッションテストを成立させる。
- leak/continuity checker の検出範囲と限界を明示し、過信を防ぐ。

## Non-Goals

- memory summary・relationship graph analytics(Phase 5)。
- 複数キャラクターの並列実行。
- pacing/character-consistency/repeated-phrase/stale-plot checker(Phase 5)。
- stop_for_review の実際の停止動作(session-autonomy の責務)。

## Decisions

### D1: Agent I/O スキーマの具体形

各 agent の入出力は以下の Pydantic モデル形状で固定する(実装詳細は tasks.md 側で確定するが、capability spec の要求はこの形状を前提にする)。

- `CharacterAgentInput`: `character_id` / `scoped_state`(本人 CharacterState) / `visible_events`(直近 N 件) / `visible_facts`(scene reader_visible_facts + 本人が見てよい hidden_facts) / `relationships`(関連ペアのみ) / `directives`(本人宛 intervention)。
- `CharacterAgentOutput`: `action_candidates: list[ActionCandidate]`(`kind: action|dialogue|inner_reaction`, `content`, `visibility`) / `emotion_deltas: list[EmotionDeltaCandidate]`(`emotion`, `delta`, `visibility`) / `goal_updates: list[GoalUpdateCandidate]`(`goal_kind: short_term|long_term`, `content`, `visibility`)。
- `WorldSimulatorOutput`: `time_advance` / `parameter_drifts: list[ParameterDriftCandidate]`(`parameter`, `delta`, `visibility`) / `faction_moves: list[FactionMoveCandidate]`(`faction_id`, `description`, `visibility`) / `background_events: list[BackgroundEventCandidate]`(`description`, `roll_id`, `visibility`)。
- `ConflictResolverOutput`: `resolved_events: list[Event]`(state-model の Event スキーマ、順序保持)。
- `StateManagerOutput`: `state_diff: StateDiff`(state-model のスキーマ、各 change は `source_event` 必須)。

理由: capability spec の各 Requirement をテスト可能な形にするには、agent 境界での型を先に固定する必要がある。state-model の Event/StateDiff を再利用することで二重スキーマ化を避ける(DRY)。

代替案: 各 agent が自由形式の dict を返し、Conflict Resolver / State Manager 側で緩く解釈する案は却下。構造化出力検証(§8)の恩恵を失い、スコープ違反の検出も後手に回る。

### D2: スコープ済みコンテキスト構築を WorldStateBundle 上の純粋関数にする

Context Builder の3関数(`build_character_context` / `build_narrator_context` / `build_world_context`)は、`WorldStateBundle`(state-model が提供する型付き全状態)を入力に取り、LLM 呼び出しを一切含まない純粋関数として実装する。

理由: スコープ不変条件は本プロダクトの中心契約であり、LLM の非決定性を排除して adversarial fixture(他者の secrets や gm_vault を意図的に含む WorldStateBundle)で単体テストできる必要がある。これにより「LLM が気まぐれに正しく振る舞う」ことに依存せず、コンテキストという入力段階で漏洩をゼロにできる。

代替案: プロンプトテンプレート内で「他者の秘密を見ないでください」と指示するのみに頼る案は却下。プロンプト指示はスコープ保証にならず、spec-foundation §4.3 の SHALL/SHALL NOT を満たせない。

### D3: Leak/Continuity Checker は正規化部分文字列一致を中心に据え、LLM 評価は warn 級オプションとする

MVP の Leak Checker / Continuity Checker は、完全一致・正規化部分文字列一致という機械的・決定的な検査を中核とする。これは mock provider でのリグレッションテストに乗る唯一の方式である。LLM ベースの評価は追加のシグナルとして任意提供するが、既定 severity を `warn` に固定し、error として auto-apply をブロックしない。

トレードオフ: 機械的一致はパラフレーズ(言い換え)による漏洩を検出できない。これは既知の限界として capability spec と本書に明記する。緩和策は二段構え: (a) LLM ベース評価をオプションで併用する、(b) 最終防波堤として GM review gate(session-autonomy)を残し、機械的検査を通過した出力も人間が確認できるようにする。

代替案: LLM ベース評価のみに一本化する案は却下。決定的な回帰テストが成立しなくなり、spec-foundation §7 の再現性契約と矛盾する。

### D4: Conflict Resolver の順序付けポリシー

resolved event の生成順序は次の優先順位で決定する: (1) intervention によって直接指示された行動、(2) 現在シーンの `active_characters` に列挙された順のキャラクター行動、(3) World Simulator の背景イベント。争われている(contested)結果は、この順序が決まった時点で random-engine に roll を要求し、roll 結果を resolved event に反映してから次の候補の解決に進む。

理由: シーンの `active_characters` 順は state-model 側で既に安定した順序を持ち、追加のソートキーを持ち込まずに決定的な順序を得られる(YAGNI: 独自の優先度スコアリングは導入しない)。intervention 優先はユーザー体験上自然であり、企画書 §7.3(GM裁定)の期待にも合致する。

代替案: 完全ランダム順序は却下(再現性が seed 依存になり過ぎ、ユーザー介入の実感が薄れる)。キャラクターごとの重要度スコアによる優先順位付けは、第1バッチでは speculative generality として見送る。

### D5: 全 active_characters に対して毎ターン Character Agent を実行する(バッチ1では非登場キャラクターはスキップ)

Character Agent は、現在シーンの `active_characters` に含まれる全キャラクターに対して毎ターン実行する。シーンに登場していないキャラクターは、そのターンでは Character Agent を実行しない(スキップする)。

理由: シーン外キャラクターの自律行動(オフスクリーンでの並行進行)は面白い要素だが、コンテキストスコープ・衝突解決・checker の対象範囲を一段複雑にする。第1バッチのスコープ(spec-foundation §1.3 の非ゴール)には含まれておらず、YAGNI に従い見送る。

## Risks & Trade-offs

- [Risk] 正規化部分文字列一致によるパラフレーズ漏洩の見逃し → Mitigation: LLM ベース warn 級評価をオプション提供し、GM review gate を最終防波堤として残す(D3)。
- [Risk] Character Agent が秘密保持のプロンプト要求を無視し、知らないはずの情報を出力に含める可能性(プロンプト遵守は保証できない) → Mitigation: enforcement は Context Builder(入力段階でのスコープ限定)と Leak/Continuity Checker(出力段階での機械的検査)の二重で行い、agent 自身の「良識」に依存しない。
- [Risk] Conflict Resolver の順序ポリシー(D4)が固定的すぎ、将来複雑な優先度ルールが必要になる可能性 → Mitigation: 現時点では YAGNI に従い固定順序で進め、必要になった時点で別 change として拡張する。
- [Risk] agent_io の全量記録が長期セッションでディスク容量を圧迫する可能性 → Mitigation: 本 change のスコープ外(第1バッチの非ゴール)とし、Phase 5 以降の運用最適化に委ねる。

## Open Questions

- Leak Checker の正規化ルール(空白・全角半角・大文字小文字)の詳細仕様は実装時に確定する。誤検出(false positive)率が高すぎる場合は正規化ルールの調整が必要になる可能性がある。
- LLM ベース leak/continuity 評価の既定 ON/OFF は、コスト・レイテンシとのトレードオフでありプロジェクト設定(`project.yaml`)側で決定する余地を残す。本 change では機能自体の提供までとする。
