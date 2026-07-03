## 1. TurnContext とターン artifact ローダー

- [ ] 1.1 `TurnContext`(Load フェーズの出力: project + state-model の各 state をメモリ上に保持する型)を定義する
- [ ] 1.2 turn artifact ディレクトリ `workspace/runs/turn_NNNN/` の命名・ゼロ埋め規約(spec-foundation §3)に従ったパス解決ユーティリティを実装する
- [ ] 1.3 「最後に `applied` されたターン + 1」で次ターン番号を決定するロジックを実装する
- [ ] 1.4 未解決ターン(`pending_review` / `stopped_for_review`)が存在する場合に次ターン実行をブロックするチェックを実装する
- [ ] 1.5 Load フェーズ(project + 全 state ファイルの読み込み → TurnContext 構築)を実装する

## 2. Artifact writer

- [ ] 2.1 `intervention.yaml` `events.yaml` `rolls.yaml` `checks.yaml` `state_diff.yaml` の書き込み(Pydantic モデル → YAML safe_dump)を実装する
- [ ] 2.2 `agent_io/` ディレクトリへの Act フェーズ入出力の書き込みを実装する
- [ ] 2.3 `meta.yaml` の書き込み(フェーズごとの所要時間、LLM 呼び出し回数、モデル名、prompt hash 一覧、rng sequence 消費数、pipeline_version)を実装する
- [ ] 2.4 例外発生時にそれまでに構築済みの artifact を破棄せず保存する部分永続化ロジックを実装する
- [ ] 2.5 人間可読のエラーレポート形式(フェーズ名・例外種別・メッセージ)を定義し `failed` ステータス時に artifact へ含める

## 3. スロット Protocol とフェーズドライバー

- [ ] 3.1 Simulate / Act / Resolve / Check の入出力を表す Pydantic モデルを定義する
- [ ] 3.2 Simulate / Act / Resolve / Check の Protocol を定義する
- [ ] 3.3 名前キーの辞書レジストリ(D108)を実装し、スロット実装の登録・取得を行う
- [ ] 3.4 TurnPipeline driver(8フェーズを順序どおり呼び出すコアループ)を実装する
- [ ] 3.5 フェーズ例外の捕捉 → 部分 artifact 保存 → ステータス `failed` 設定の異常系パスを実装する
- [ ] 3.6 llm-provider からの型付き例外(retry 最終失敗)を Act フェーズ失敗として扱う配線を実装する

## 4. 組み込み最小スロット実装

- [ ] 4.1 Simulate: no-op world simulator(候補イベントを生成しない)を実装する
- [ ] 4.2 Act: llm-provider 経由で単一キャラクターの行動候補を1件生成する trivial 実装を実装する
- [ ] 4.3 Resolve: 行動候補・イベント候補を乱数判定なしでそのまま events.yaml へ渡す pass-through 実装を実装する
- [ ] 4.4 Check: 常にエラーを検出しない no-op checker を実装する
- [ ] 4.5 組み込みスロットをレジストリへデフォルト登録する初期化コードを実装する

## 5. Narrator と renderer

- [ ] 5.1 Reader State + シーンの reader_visible_facts + 今ターンの reader 可視イベントのみから Narrator 入力を構築するコンテキスト抽出ロジックを実装する(GM Vault / hidden_facts / 他者 private_mind を除外することを検証可能な形で実装する)
- [ ] 5.2 renderer レジストリ(D108)を実装する
- [ ] 5.3 `novel` renderer(小説風連続散文)を実装する
- [ ] 5.4 `log` renderer(ターン/イベント箇条書き)を実装する
- [ ] 5.5 未登録 renderer 名指定時に明示的エラーを送出する処理を実装する
- [ ] 5.6 Narrator に mood / tone_control 制約値を guidance として渡す呼び出しインターフェースを実装する
- [ ] 5.7 `narration.md` のフロントマター(`turn` / `style` / `visibility: reader`)+本文の書き出しを実装する
- [ ] 5.8 Narrate フェーズを TurnPipeline に接続する

## 6. ターンステータスと Commit フェーズ

- [ ] 6.1 ターンステータス列挙(`applied` / `pending_review` / `stopped_for_review` / `failed`)を定義し artifact へ記録する
- [ ] 6.2 Check フェーズの error 級検出結果に基づき `stopped_for_review` へ遷移させ、Commit の diff 適用をスキップするロジックを実装する
- [ ] 6.3 Commit フェーズ: Resolve/Check の結果から state diff を生成し state-model の diff 適用インターフェースへ渡す処理を実装する
- [ ] 6.4 commit-mode フラグ(`auto` | `review`)の読み込みと、`auto` → 即時適用 / `review` → `pending_review` 据え置きの分岐を実装する

## 7. テスト

- [ ] 7.1 mock provider + 組み込みスロットで1ターンが例外なく完走し、8つの artifact ファイルがすべて生成されることを検証する end-to-end pytest を書く
- [ ] 7.2 同一 seed + 同一構成で2回ターンを実行し、生成される events.yaml / narration.md / meta.yaml(rng sequence 等)が一致することを検証する再現性テストを書く
- [ ] 7.3 フェーズ例外(Narrate 内で例外を強制発生)時に部分 artifact が保存され `failed` になることを検証するテストを書く
- [ ] 7.4 Check フェーズが error 級結果を返す場合に `stopped_for_review` になり diff が未適用のままであることを検証するテストを書く
- [ ] 7.5 commit-mode `auto` / `review` それぞれでステータスが `applied` / `pending_review` になることを検証するテストを書く
- [ ] 7.6 未解決ターンが存在する場合に次ターン実行がブロックされることを検証するテストを書く
- [ ] 7.7 Narrator 入力に GM Vault / hidden_facts が含まれないことを検証するテストを書く
- [ ] 7.8 `novel` / `log` renderer それぞれの出力形式と、未登録 renderer 名でのエラー送出を検証するテストを書く

## 8. ドキュメント

- [ ] 8.1 `docs/spec-foundation.md` の該当箇所(§6)との対応を確認し、実装差分があれば矛盾がないことを確認する(仕様側の更新は不要な想定だが、齟齬発見時は別途報告する)
- [ ] 8.2 turn artifact ディレクトリの構造・各ファイルの役割を README または `docs/` に簡潔に記載する
