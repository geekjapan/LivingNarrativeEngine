## Why

企画書 §7 の6つの体験(観測・介入・GM裁定・作者・PC参加・ログ化)を1つのエンジンで支えるには、「誰が何をできるか」(user mode)と「どこまで自動で進めるか」(autonomy level)を独立した契約として定義し、両者の組み合わせを検証し、GM レビューゲート・停止条件・セッション再開という共通フローに束ねる capability が必要である。intervention capability が個々の介入の意味論を定義した上で、本 change はその介入をいつ・誰が・どこまで自律的に発行できるかを規定する。

## What Changes

- 企画書 §8 の6ユーザーモード(watcher / assistant_gm / full_gm / author / player_character / god)を、許可される介入タイプ集合(型の一覧自体は intervention capability が正本)・state diff レビュー要否・gm_vault 表示可否からなる権限マトリクスとして定義する。
- `player_character` モードが特定の `char_id` に紐づき、ユーザー入力が当該キャラクターの行動候補として直接ルーティングされる仕組みを追加する。
- 企画書 §9 の5自律性レベル(manual / assist / auto / watch / god)の意味論を定義する。
- user_mode × autonomy_level の組み合わせを検証し、矛盾する組み合わせを警告付きで正規化するルールを追加する。
- 企画書 §10.6 の9つの停止条件(キャラクター死亡・重大Canon変更・関係性閾値超過・重大秘密開示・checkerエラー・リーク疑い・重い判定失敗・シーン終了・目標ターン到達)の判定ロジックと、レベルごとの適用有無を定義する。停止条件はプロジェクト単位で有効/無効・閾値を設定できる。
- 企画書 §10.10 の GM レビューゲート(accept all / reject all / partial / edit / rerun turn)のフロー契約を定義し、決定を `review.yaml` に記録する。
- rerun 実行時の乱数消費セマンティクス(既定: 新規シーケンス消費、フラグ指定で同一シード再現)を定義する。
- ワークスペースのみから最終適用ターン・pending review・mode/level 設定を復元する resume を追加する。resume は pending review を最優先で提示する。
- 指定ターン数または停止条件までの auto ループ(中断安全)を追加する。
- God mode の編集操作を常に diff として発行・記録する仕組み(レビューはバイパスするが artifact ログは決してバイパスしない、D107)を追加する。

## Capabilities

### New Capabilities

- `session-autonomy`: user mode の権限マトリクス、autonomy level の意味論、mode×level 正規化、停止条件評価、GM レビューゲート、resume、auto ループ、God mode のログ強制を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- ブランチ管理の UX(データ形式は state-model capability が既に定義済み。運用機能は Phase 5)。
- 介入候補のサジェスト機能(watch レベルでの「介入候補提示」の中身生成ロジックは対象外。本 change は候補提示のオン/オフとレベル適用のみを扱う)。
- Web UI。GM レビューゲート・resume・auto ループの CLI 上での具体的なレンダリングは `cli` capability が担当する。本 capability はフロー契約のみを規定する。

## Dependencies

- `add-intervention`(介入タイプの列挙・スキーマ・Interpreter・可視性を提供する。本 change はそれを user_mode に束ねる)。intervention は transitively `add-turn-pipeline`(ターン artifact 構造・失敗ポリシー)・`add-state-model`(state diff 形式)・`add-random-engine`(rerun の乱数セマンティクス)に依存する。

## Impact

- 新規コード: `src/living_narrative/session/`(`mode.py` `autonomy.py` `stop_conditions.py` `review.py` `resume.py` 相当。企画書 §18.3 のディレクトリ構成に準拠)。
- 新規 artifact: 各 `workspace/runs/turn_NNNN/review.yaml`。
- 既存 artifact への影響: `meta.yaml` の rng 消費数を resume/rerun が読み取る(add-random-engine 定義済み)。
- 統合ポイント: turn pipeline の Intervene フェーズ(player_character 入力ルーティング)、Check→Commit 境界(停止条件評価点)。
- 依存する将来 change: `add-cli-and-sample`(mode/level の CLI フラグ、レビューゲート・resume・auto ループのレンダリング)。
