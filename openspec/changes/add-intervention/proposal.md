# Proposal: add-intervention

## Why

企画書 §5.2 は「ユーザーの指示はプロンプトとして消費して消すのではなく、第一級オブジェクトとして保存する」ことを核心原則としている。`add-turn-pipeline` は Intervene フェーズを無介入(空の `intervention.yaml`)で仮実装しており、`add-agent-runtime` はキャラクター・世界の実行主体を提供した。両者を繋ぎ、ユーザーの自由文/構造化指示を型付き Intervention に変換し、権限を検査し、各実行主体へ配線する capability がなければ、本プロダクトの中核体験(観測・介入・裁定・演出・演者参加。企画書 §7.2-7.5)は成立しない。

## What Changes

- 企画書 §14.8 準拠の Intervention スキーマ(id/turn/user_role/type/target/content/constraints/visibility)を追加する。`type` は企画書 §10.7 の全15種を enum として持つ。
- 15種のうち `scene_directive` `character_directive` `world_directive` `event_injection` `tone_control` `reveal_control` `dice_roll_request` `canon_edit` `hidden_truth_edit` の9種について、パイプラインへの具体的なルーティング・実行動作を本 change で実装する(バッチ1対象)。`stop_condition` は本 change 内では専用ルーティングを実装しないが、`intervention.yaml` への保存を通じて `session-autonomy` capability の停止条件評価(10番目の停止条件、Check→Commit の境界、全 autonomy レベル(watch/god 含む)で停止。D119)に消費される、明示的な消費先を持つ type として扱う。
- 残る5種(`probability_bias` `pacing_control` `scene_pivot` `relationship_edit` `memory_edit`)はスキーマ上受理・`intervention.yaml`/履歴に永続化・関係する agent のコンテキストへ constraints として提示する — が、専用ハンドラ(状態への具体的な反映ロジック)は本 change には含めない。
- Intervention Interpreter を追加する: ユーザー自由文を入力に、llm-provider の構造化出力経由で1件以上の Intervention を生成する。各出力には confidence(0-1)と人間可読な解釈要約(interpretation summary)を含める。
- 構造化直接入力パス(LLM を経由せず、型付き Intervention を直接構築する経路)を追加する。CLI フラグ・テストからの決定的な入力に使う。
- Role permission hook を追加する: intervention 生成時(Interpreter 経由・直接入力経路の両方)に、プラガブルな permission 判定関数(データ注入された permission table により type×user_mode の許可可否を決める)を通して強制する。intervention capability がハードコードするのは普遍的不変条件(`canon_edit`/`hidden_truth_edit` は `full_gm`/`god` のみ許可)のみであり、type×user_mode の15種×6モード完全マトリクスの正本は session-autonomy 起点(企画書§8のモード定義)であるため `session-autonomy` capability が持つ(D114)。`session-autonomy` が未配線の場合の既定 permission table は、上記不変条件を除き全許可(permissive)とする。許可されない場合、システムは Intervention を生成せず、type・要求された user_mode・許可されている user_mode 集合を含む型付き rejection を返す。
- パイプライン統合: intervention は spec-foundation §6 フェーズ2(Intervene)で消費され、`intervention.yaml` に保存される。効果は以下へルーティングされる:
  - `character_directive` → 対象キャラクターのコンテキストのみ
  - `world_directive` / `event_injection` → World Simulator
  - `tone_control` / `reveal_control` → Narrator 制約
  - `dice_roll_request` → Random Engine(Conflict Resolver 経由)
  - `canon_edit` / `hidden_truth_edit` → State Manager 経由の直接 state diff エントリ(D107: 直接書き換え禁止、diff 経由のみ)
- `reveal_control` の意味論を追加する: 事実を「開示禁止(must-not-reveal)」または「即時開示(reveal-now)」としてマークする。実際の強制点は spec-foundation §6 フェーズ8(Commit)内の BuildDiff スロット(agent-runtime の State Manager が実装、turn-pipeline がスロット契約を定義。D113)であり、must-not-reveal は Reader State への昇格をブロックし、reveal-now は diff 変更として emit され Reader State へ昇格される。intervention capability の責務は BuildDiff が参照する制約データ(must-not-reveal / reveal-now マーク)を生成することのみであり、turn-pipeline 側への新規 hook 追加は不要(Modified Capabilities なし)。
- Intervention 履歴インデックス(`interventions.yaml`)を追加する: プロジェクト全体で累積し、各 intervention から結果として生じた event / state diff への参照(source reference)により追跡可能にする。

## Capabilities

### New Capabilities

- `intervention`: Intervention スキーマ、Interpreter(自由文解釈)、構造化直接入力、role permission hook、パイプラインルーティング、reveal_control 意味論、履歴インデックスを提供する。

### Modified Capabilities

(なし)

## Non-Goals

- Intervention の「提案」機能(システム側からユーザーへ次の介入候補を提示する。企画書の後続フェーズ項目)は対象外。将来 change として別途提案する。
- God Mode の任意編集 UI(企画書 §8.6 の Canon 編集・巻き戻し等を行うための対話的 UI)は対象外。本 change は God Mode を含む permission 判定とデータ経路のみを提供する。
- Web UI からの介入入力は対象外(第1バッチは CLI のみ、spec-foundation D101)。
- Interpreter の解釈結果をユーザーに提示・確認させる画面/CLI フロー(assist モードでの「実行前に見せる」表示配線)は `session-autonomy` / `cli` capability の責務。本 change はそのために必要なデータ(confidence・summary)を提供するのみ。
- `probability_bias` `pacing_control` `scene_pivot` `relationship_edit` `memory_edit` の専用実行ロジック(状態への具体的反映)は対象外(上記 What Changes 参照。将来 change で追加)。`stop_condition` の停止条件評価ロジック自体も本 change の対象外だが(D119、`session-autonomy` capability が実装)、消費先が明示されている点で残る5種とは異なる。

## Dependencies

- `add-agent-runtime`(character_directive / world_directive / event_injection / tone_control / reveal_control / canon_edit / hidden_truth_edit のルーティング先である Character Agent / World Simulator / Narrator / State Manager が実装済みであること)。
- `add-llm-provider`(Intervention Interpreter が使う構造化出力 provider protocol)。
- 推移的に `add-turn-pipeline`(Intervene フェーズの契約・`intervention.yaml` artifact 形式)と `add-state-model`(StateDiff 形式、target enum)にも依存する。

## Impact

- 新規パッケージ `living_narrative.intervention`(schema / interpreter / direct_input / permissions / router / history のサブモジュール)。
- 新規 artifact: 各 `workspace/runs/turn_NNNN/intervention.yaml`、プロジェクト全体の `workspace/interventions.yaml`(履歴インデックス)。
- `add-turn-pipeline` が定義した Intervene フェーズの no-op 実装を本 change の実装で置き換える。
- 依存する将来 change: `add-session-autonomy`(interpreter の confidence を用いた assist モードの表示・確認フロー、permission rejection 後のユーザーへの提示)。
