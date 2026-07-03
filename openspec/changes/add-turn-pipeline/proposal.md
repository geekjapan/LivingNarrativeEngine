# Proposal: add-turn-pipeline

## Why

state-model / random-engine / llm-provider が揃っても、それらを spec-foundation §6 の 8 フェーズ順序で結び付け、
ターンごとの artifact を確定形式で残す実行基盤が無ければ「1ターンを回す」ことができない。
また、後続の `add-agent-runtime` が Simulate/Act/Resolve/Check の各スロットを実装として差し替えられるようにするには、
その前に呼び出し順序・入出力契約・artifact 形式・失敗処理を固定した pipeline driver が必要である。
本 change は、mock provider と最小限の組み込みスロットで、ターンを最初から最後まで決定的に実行できる状態を作る。

## What Changes

- spec-foundation §6 の 8 フェーズ(Load / Intervene / Simulate / Act / Resolve / Narrate / Check / Commit)を
  この順序で実行する `TurnPipeline` driver を追加する。
- Simulate / Act / Resolve / Check の 4 フェーズを Protocol による差し替え可能スロットとして定義する(D108: レジストリ辞書、plugin loader は作らない)。
- 各スロットの最小組み込み実装を追加し、mock provider だけでターンが最初から最後まで実行できるようにする:
  - Simulate: 何もしない no-op world simulator(候補イベントを生成しない)。
  - Act: llm-provider 経由で単一キャラクターの行動候補を1件生成する trivial 実装。
  - Resolve: 行動候補・イベント候補をそのまま(乱数判定を経ずに)events.yaml へ通す pass-through 実装。
  - Check: 常に checker エラーを出さない no-op checker。
- Load フェーズを追加する: project + 全 state ファイルを読み込み、メモリ上の `TurnContext` を構築する。
- Intervene フェーズを追加する: この change では構造化 intervention の解釈は行わず、無介入として `intervention.yaml` を空で書き出す(interpreter は `add-intervention` で追加)。
- Commit フェーズを追加する: Resolve/Check の結果から state diff を生成し、state-model の diff 適用に渡す。
  適用するか pending にするかは、この change ではプロジェクト設定の単純な commit-mode フラグ(`auto` / `review`)で決める(session-autonomy の判断ロジックは対象外)。
- turn artifact ディレクトリ `workspace/runs/turn_NNNN/` への書き込みを追加する: `intervention.yaml` `agent_io/` `events.yaml` `rolls.yaml` `narration.md` `checks.yaml` `state_diff.yaml` `meta.yaml`。
- `meta.yaml` にフェーズごとの所要時間・LLM 呼び出し回数・使用モデル名・prompt hash 一覧・消費した rng sequence・pipeline version を記録する。
- ターンステータスモデル(`applied` / `pending_review` / `stopped_for_review` / `failed`)を artifact に記録し、次ターン番号の決定(最後に `applied` されたターン+1)と、未解決ターンによる後続ターンのブロックを実装する。
- spec-foundation §6 の失敗ポリシーを実装する: スキーマ不一致の retry は llm-provider に委譲し、pipeline はフェーズ例外を捕捉して途中までの artifact を保存し、status を `failed` にして人間可読のエラーレポートを artifact に含める(例外を握り潰さない)。
- Narrator(`narration` capability)を追加する: reader 可視情報のみから日本語散文を生成し、`novel` / `log` の renderer レジストリ(D108)で出力形式を切り替える。scene の mood と intervention の tone_control 制約(値は受け取るが解釈は最小限)を長さ・トーンの guidance として利用する。

## Capabilities

### New Capabilities

- `turn-pipeline`: 8 フェーズの実行順序、スロット Protocol、組み込み最小スロット、turn artifact 書き込み、meta.yaml、ターンステータス管理、失敗処理、commit-mode フラグを提供する。
- `narration`: reader 可視情報のみからの日本語散文生成、novel/log renderer レジストリ、narration.md artifact を提供する。

### Modified Capabilities

(なし)

## Non-Goals

- 実際の Character Agent / World Simulator / Conflict Resolver(`add-agent-runtime` で組み込みスロットを置き換える)。
- ユーザー自由文の intervention 解釈(`add-intervention`)。
- 自律進行(3ターン進行・シーン終了まで等)・停止条件判定・GM review gate の意思決定ロジック(`add-session-autonomy`)。commit-mode フラグはその暫定代替であり、恒久仕様ではない。
- TRPGリプレイ風・脚本風・ビジュアルノベル台本風の narration 出力(Phase 6+)。
- 過去ターンの narration 再生成コマンド(データ形式は再生成を妨げないが、コマンド自体は本 change の対象外)。

## Dependencies

- `add-state-model`(TurnContext のロード元、state diff の生成・適用先)。
- `add-random-engine`(Resolve フェーズでの rng 消費数記録に必要。本 change の pass-through Resolve 実装自体は乱数判定を行わないが、`rolls.yaml` の空ファイル形式・meta.yaml の rng sequence フィールドは random-engine の契約に従う)。
- `add-llm-provider`(Act フェーズの trivial 実装、mock provider による決定的な end-to-end 実行)。

## Impact

- 新規: `src/living_narrative/pipeline/`(driver, slots protocol, 組み込み slot 実装, artifact writer, status)、`src/living_narrative/narration/`(narrator, renderer registry, novel/log renderer)、`tests/pipeline/`、`tests/narration/`。
- 新規 artifact: `workspace/runs/turn_NNNN/` 以下の全ファイル。
- 依存する将来 change: `add-agent-runtime`(Simulate/Act/Resolve/Check スロットの実装差し替え)、`add-intervention`(Intervene フェーズの実装差し替え)、`add-session-autonomy`(commit-mode フラグを autonomy の判断ロジックへ置き換え)。
