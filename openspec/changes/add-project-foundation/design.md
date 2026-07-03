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
`init` はコード内に埋め込んだ最小の空ワールドテンプレート(Python の辞書/文字列リテラルまたは同梱の小さな YAML ファイル)から生成する。テンプレートエンジン(Jinja2 等)は本 change の範囲では導入しない。物語コンテンツを持つ本格的なサンプルテンプレートの差し替えは `add-cli-and-sample` で行う。

## Risks & Trade-offs

- [Risk] `project.yaml` スキーマを本 change で固定すると、後続 change (`add-state-model` 等)で追加フィールドが必要になった際に破壊的変更が生じうる。
  → Mitigation: 未知フィールドを警告のみで許容する設計とし、フィールド追加を非破壊にする。将来的な必須化は別 change で明示的に提案する。
- [Risk] typer によるコマンド体系を早期に固定すると、`add-cli-and-sample` での拡張時に構造の手戻りが発生しうる。
  → Mitigation: 本 change では `init` 1コマンドのみを実装し、サブコマンド追加を前提とした app 構造(単一 typer app + サブコマンド登録)に留める。

## Open Questions

- 実 LLM 利用時の既定 provider/model は未決(spec-foundation §10、`add-llm-provider` 側で扱う)。本 change の `project.yaml` スキーマでは `llm.provider`/`llm.model` を任意値として受け付けるのみで、既定値の是非には立ち入らない。
