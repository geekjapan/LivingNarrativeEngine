# Design: add-project-foundation

## Context

Living Narrative Engine の第1実装バッチの起点となる change。リポジトリには現状コードが存在せず(`README.md` と `AGENTS.md` のみ)、以降の全 change(`add-state-model` 以降)が依存する土台を確立する必要がある。

## Goals

- `uv` ベースの Python 3.12+ 開発環境を整え、CI で lint・test を自動化する。
- `project.yaml` の読み込み・検証を、後続 change が安心して積み上げられる程度に堅牢にする(複数エラーの集約報告)。
- 企画書 Appendix C の workspace レイアウトを固定し、`init` で再現可能にする。

## Non-Goals

- CLI コマンド群全体・サンプル世界の作り込みは `add-cli-and-sample` に委譲する。
- `project.yaml` 以外の state ファイルのスキーマは `add-state-model` に委譲する。
- Web UI・DB は第1バッチの非ゴール(spec-foundation §1.3, D103)。

## Decisions

### D102 (再掲・適用): CLI フレームワークに typer を採用
企画の決定ログ D102 を本 change で最初に適用する。`init` はサブコマンドの1つとして実装し、後続 change (`add-cli-and-sample`) が同じ typer app にサブコマンドを追加できる構造にする。
- 代替案: `argparse`(標準ライブラリで依存追加不要だが、サブコマンド・型ヒント連携のボイラープレートが増える)。typer は型ヒントから自動でオプションを生成でき、以降のコマンド追加コストが低いため採用。

### D103 (再掲・適用): 状態の正本はファイル、DB は導入しない
`project.yaml` および workspace 配下の state ファイルは YAML を正本とする。本 change ではロード時 Pydantic 検証のみを行い、インデックスや DB へのミラーリングは行わない。
- 理由: 人間可読性・git 差分の追いやすさ・rollback の容易さ(spec-foundation D103)。将来的に DB を導入する場合も「派生インデックス」として位置づけ、正本の地位は変更しない。

### src レイアウトの採用
`src/living_narrative/` 配下にパッケージを置く(企画書 §18.3 のディレクトリ構成に準拠)。
- 理由: テスト実行時に誤って未インストールのリポジトリ直下パッケージを import してしまう事故を防ぎ、`uv sync` でインストールされたパッケージのみを対象にテストできる。AGENTS.md の推奨レイアウト(`src/`/`tests/`)とも整合する。

### uv によるパッケージ管理
`pip`/`venv` 手動運用ではなく `uv` を採用(企画書 §2 技術スタック確定事項、spec-foundation §2)。
- 理由: lockfile による再現性、`uv sync`/`uv run` の高速性。企画書で既に確定済みの選択であり、本 change で再検討しない。

### project.yaml 検証のエラー集約方式
Pydantic v2 の `ValidationError` はデフォルトで複数エラーをまとめて保持できるため、これをそのまま活用し、フィールドパス・理由をアプリケーション側でファイルパスと合わせて整形する薄いラッパーを設ける。専用の検証フレームワークやカスタム DSL は導入しない(YAGNI)。

### init のテンプレート方式
`init` はコード内に埋め込んだ最小の空ワールドテンプレート(Python の辞書/文字列リテラルまたは同梱の小さな YAML ファイル)から生成する。テンプレートエンジン(Jinja2 等)は本 change の範囲では導入しない。物語コンテンツを持つ本格的なサンプルテンプレートの差し替えは `add-cli-and-sample` で行う。`--title` 以外のフィールドは固定既定値(spec 参照)を用いる。`add-cli-and-sample` は同じ `init` サブコマンドに `--genre`/`--tone`/`--template`/`--output` を追加し、`mist_station`/`minimal` のテンプレート選択を導入する計画であり、本 change の `init` はその前段の最小実装として位置づける。

## Risks & Trade-offs

- [Risk] `project.yaml` スキーマを本 change で固定すると、後続 change (`add-state-model` 等)で追加フィールドが必要になった際に破壊的変更が生じうる。
  → Mitigation: 未知フィールドを警告のみで許容する設計とし、フィールド追加を非破壊にする。将来的な必須化は別 change で明示的に提案する。
- [Risk] typer によるコマンド体系を早期に固定すると、`add-cli-and-sample` での拡張時に構造の手戻りが発生しうる。
  → Mitigation: 本 change では `init` 1コマンドのみを実装し、サブコマンド追加を前提とした app 構造(単一 typer app + サブコマンド登録)に留める。

### D118 (再掲・適用): commit_mode は project.yaml フィールドではない
`commit_mode` はターン実行 API のランタイムパラメータであり、`project.yaml` の `llm` にも他の箇所にもスキーマフィールドとして追加しない(spec-foundation D118)。理由: `commit_mode` は `session-autonomy` が正式に置換する暫定的な実行時概念であり、プロジェクト永続設定としてスキーマに固定するとスキーマ汚染・将来の破壊的変更リスクを招く。対して `llm.timeout_seconds`(既定 `30`)・`llm.prompt_recording`(`full`|`hash_only`、既定 `full`)はプロジェクト単位で永続すべき設定であり、`add-llm-provider` が LLM 呼び出し時にこれらを消費する前提で `project.yaml` `llm` に正式追加する。

### D117 (再掲・適用): 必須7 state ファイルは fail-fast、`add-state-model` 側と整合
本 change の「必須 state ファイルの存在確認」Requirement(欠落 → 読み込み失敗・検証レポート)は、spec-foundation D117 により canonical policy として確定した。`add-state-model` 側の `StateStore.load` も、必須7ファイル(`world.yaml`, `canon.yaml`, `reader_state.yaml`, `gm_vault.yaml`, `relationships.yaml`, `timeline.yaml`, `unresolved_threads.yaml`)の欠落については同じく fail-fast(集約エラー)に修正され、存在するが空のファイルのみを空コレクションとして扱う。これにより Grill Q1 で指摘された「同一シナリオへの正反対の契約」の矛盾は解消された。両 API の役割分担は次のとおり: `StateStore.load` はパイプラインの Load フェーズが呼ぶ唯一のロード経路であり、必須ファイル欠落時に集約エラーで fail-fast する。本 change の「プロジェクト読み込み API」の存在確認は、`init`/`status` 等が使う高速な事前チェック(ファイル内容のスキーマ検証は行わず存在のみを見る)であり、`StateStore.load` の代替ではない。

### init コマンドの所有権 — `add-cli-and-sample` が MODIFIED delta で置換
本 change の「init コマンドによるプロジェクト作成」Requirement(`--title` のみ必須、固定既定値版)は最小実装の暫定版である。`add-cli-and-sample` は proposal.md の Capabilities 節で `project-workspace` を Modified Capabilities として宣言しており、アーカイブ時に `init` Requirement を `--genre`/`--tone`/`--template`/`--output` とテンプレート選択(`mist_station`/`minimal`)を持つ完成版へ MODIFIED delta として置き換える計画である。本 spec.md の `init` Requirement 自体はそのまま(置換対象のベースとして)残し、変更しない — 置換は `add-cli-and-sample` 側の spec delta の責務であり、本 change のドキュメントを書き換える必要はない。

## Open Questions

- 実 LLM 利用時の既定 provider/model は未決(spec-foundation §10、`add-llm-provider` 側で扱う)。本 change の `project.yaml` スキーマでは `llm.provider`/`llm.model` を任意値として受け付けるのみで、既定値の是非には立ち入らない。
