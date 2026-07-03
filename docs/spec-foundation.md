# Spec Foundation — 共有契約

全 OpenSpec change / capability spec が参照する横断契約。ここに書かれた規約と矛盾する spec は誤り。
ビジョン・背景・ロードマップは `docs/project_plan.md` を参照(本書は規範、企画書は動機)。

作成日: 2026-07-03 / 対象バッチ: 第1実装バッチ(Text MVP + Core Runtime + Intervention + Autonomy)

---

## 1. スコープ地図

### 1.1 Capability 一覧(第1バッチ)

| capability | 内容 | change |
|---|---|---|
| `project-workspace` | project.yaml、workspace レイアウト、init/load | add-project-foundation |
| `state-model` | 全状態スキーマ、情報スコープ、state diff 形式、state store | add-state-model |
| `random-engine` | seed、ダイス、判定、weighted table、roll ログ | add-random-engine |
| `llm-provider` | provider 抽象、mock、OpenAI互換、構造化出力 | add-llm-provider |
| `turn-pipeline` | ターン実行順序、turn artifact、失敗処理 | add-turn-pipeline |
| `narration` | ナレーター、出力形式(novel/log)、可視情報制約 | add-turn-pipeline |
| `agent-runtime` | Context Builder、Character Agent、World Simulator、Conflict Resolver、State Manager | add-agent-runtime |
| `consistency-checks` | leak check、continuity check(基本) | add-agent-runtime |
| `intervention` | 介入スキーマ、Interpreter、可視性、履歴 | add-intervention |
| `session-autonomy` | user mode、autonomy level、stop condition、GM review gate、resume | add-session-autonomy |
| `cli` | `living-narrative` コマンド群 | add-cli-and-sample |
| `export-replay` | Markdown リプレイ出力 | add-cli-and-sample |

### 1.2 Change 依存 DAG

```text
add-project-foundation
        │
        v
  add-state-model
        │
   ┌────┴─────┐
   v          v
add-random  add-llm-provider
   └────┬─────┘
        v
add-turn-pipeline      (state+random+llm に依存)
        v
add-agent-runtime      (pipeline のスロットに agent を実装)
        v
add-intervention       (interpreter は llm-provider、適用は pipeline)
        v
add-session-autonomy   (stop condition / review gate / resume)
        v
add-cli-and-sample     (CLI 完成、サンプル世界、20ターン smoke test)
```

### 1.3 第1バッチに含めないもの(非ゴール)

Web UI(FastAPI/HTMX)、SQLite、画像・音声生成、小説原案 export(replay のみ)、
TRPG/RPG ルール、マルチユーザー、memory summary・foreshadowing ledger(Phase 5)、
branch/rollback の UI(データ形式のみ将来対応可能に保つ)。

---

## 2. 技術スタック(確定)

| 項目 | 決定 | 備考 |
|---|---|---|
| 言語 | Python 3.12+ | 企画書 §18 |
| パッケージ管理 | uv(`pyproject.toml`) | dev extra に pytest/ruff |
| スキーマ | Pydantic v2 — **スキーマの単一正本** | YAML はロード時に必ず検証 |
| YAML | PyYAML `safe_load` / `safe_dump` | |
| CLI | typer | `living-narrative` エントリポイント |
| LLM client | `openai` SDK + 設定可能な `base_url` | OpenAI互換/Ollama/LM Studio を1実装で担う。LiteLLM は不採用(YAGNI) |
| テスト | pytest(mock provider で決定的に) | |
| lint | ruff(format + lint) | mypy は任意・後続 |
| DB / Web | **第1バッチでは無し** | 状態の正本はファイル。DB は将来「派生インデックス」として導入(D103) |

パッケージ名 `living_narrative`、リポジトリ構成は企画書 §18.3 に準拠(web/ 関連は第1バッチでは作らない)。

---

## 3. ID・命名規約

- ID は `<type>_<zero-padded番号>`: `char_001` `faction_001` `scene_001` `world_001`
  `event_0001` `int_0001` `roll_0001` `diff_0001` `thread_001` `fact_001`
- 例外: relationship は独自 id を持たず、有向複合キー `<from_id>__<to_id>`(例 `char_001__char_002`)で特定する(D116)
- ターン番号は 1 始まりの整数。turn artifact ディレクトリは `turn_0001` 形式。
- diff / event / roll / intervention はターンを跨いで一意(プロジェクト内通番)。
- capability・ドキュメントファイル名は kebab-case、Python は PEP8。
- YAML キーは snake_case。
- 正準 enum(全 spec でこの表記を使用):
  - `user_mode`: `watcher` | `assistant_gm` | `full_gm` | `author` | `player_character` | `god`
  - `autonomy_level`: `manual` | `assist` | `auto` | `watch` | `god`
  - turn status: `applied` | `pending_review` | `stopped_for_review` | `failed`
  - checker severity: `info` | `warn` | `error`

---

## 4. 情報スコープモデル(最重要契約)

### 4.1 スコープ定義

| スコープ | 保持場所 | 見える者 |
|---|---|---|
| GM Vault | `gm_vault.yaml` | システム/GM(ユーザーのGM系モード)のみ |
| Canon | `canon.yaml` | 世界の確定事実。読者可視とは限らない |
| Character Knowledge | `characters/*.yaml` の `knowledge` | 当該キャラクター |
| Private Mind | `characters/*.yaml` の `private_mind` | 当該キャラクター本人のみ(他 agent へ渡さない) |
| Scene | `scenes/*.yaml`(`reader_visible_facts` / `hidden_facts`) | シーン参加者(hidden はスコープ指定に従う) |
| Reader State | `reader_state.yaml` | ユーザー/読者に開示済みの情報 |

### 4.2 可視性(visibility)

Event / Fact / Intervention は `visibility` を持つ:
`gm_only` | `canon` | `character` (+`known_by: [char_id]`) | `scene` | `reader`。
派生規則: `reader` に出す情報は canon か「読者向け演出」でなければならない。
`known_by` / `hidden_from` により同一イベントでもキャラクター間の知識差を表現する。

### 4.3 コンテキスト構築の不変条件

1. Character Agent のコンテキスト = 本人の state + 本人の knowledge + 本人が参加する scene の可視情報 + 本人宛 directive。他者の private_mind・GM Vault・未知イベントは**含めてはならない**。
2. Narrator のコンテキスト = Reader State + 現シーンの reader_visible_facts + 今ターンの reader可視イベント。GM Vault・hidden_facts・他者の secrets は**含めてはならない**。
3. World Simulator / State Manager は全状態を参照できるが、出力の visibility を必ず付与する。
4. Leak Checker は Narration 出力を Reader State と照合し、未開示情報の漏洩を検出する。

### 4.4 停止条件判定用フィールド(D123)

session-autonomy の停止条件は state/roll の具体的フィールドから機械的に評価可能でなければならない(自然文の解釈や推測に頼ってはならない)。

- `CharacterState.status`: `alive` | `dead` | `missing`(既定 `alive`)。`character_death` は `dead` への遷移(state diff の `op: set, path: status`)で判定する。
- `SceneState.status`: `active` | `ended`(既定 `active`)。`scene_end` は `ended` への遷移で判定する。誰がこの diff を発行するか(World Simulator か Conflict Resolver か)は `agent-runtime` capability の責務。
- Roll record の任意フィールド `severity`: `normal` | `critical`(既定 `normal`)。`heavy_roll_failure` は `severity == critical` かつ `outcome` が失敗を示す roll で判定する(critical な高リスク行動が成功した場合は停止しない)。`severity` は呼び出し側(Conflict Resolver)が明示的に指定する値であり、random-engine は自動判定ロジックを持たない(判定基準は agent-runtime 側の設計判断)。

---

## 5. データモデル概要

スキーマ詳細は `state-model` spec が正本。ここでは形と役割のみ規定する。
全ファイルは Pydantic モデルでロード時検証。未知フィールドは警告(forbid ではなく将来互換)。

- **project.yaml** — id/title/genre/tone/language/autonomy_level/user_mode/random_seed/renderer/llm(provider,model,base_url,timeout_seconds=30,prompt_recording=full|hash_only)/workspace paths(企画書 Appendix B 準拠)。commit-mode はランタイムパラメータでありスキーマに含めない(D118)
- **LLM プロファイル(D122)** — `llm` は既定プロファイル。任意の `llm_profiles`(名前付きプロファイル辞書、各値は `llm` と同スキーマ)と `llm_bindings`(binding key → プロファイル名)で、エージェント種別・キャラクター単位に異なる LLM を割り当てられる。binding key: `narrator` | `world_simulator` | `conflict_resolver` | `state_manager` | `checker` | `interpreter` | `character_default` | `character:<char_id>`。解決順: `character:<id>` → `character_default` → 既定 `llm`(キャラクター以外は `<role>` → 既定 `llm`)。未定義プロファイル名への binding はロード時検証エラー
- **world.yaml** — id/name/summary/laws[]/parameters{public_order, danger_level, ...}(0-100 整数)
- **factions**(world.yaml 内 or factions.yaml)— goals/resources/relations
- **characters/*.yaml** — id/name/role/traits/goals(short_term/long_term)/emotions(0-100)/knowledge(knows/believes/does_not_know)/secrets/private_mind/inventory/constraints
- **relationships.yaml** — 有向ペア: trust/affection/tension/suspicion(0-100)+notes
- **scenes/scene_XXX.yaml** — location/time/active_characters/mood/stakes/reader_visible_facts(list[str])/hidden_facts(構造化: id=fact_NNN, text, visibility, known_by — per-fact スコープを表現する。D115)
- **canon.yaml** — 確定事実のリスト(id, text, established_turn, source_event)
- **reader_state.yaml** — 読者開示済み事実のリスト(同上+開示ターン)
- **gm_vault.yaml** — 隠された真実(id, text, reveal_condition?)
- **timeline.yaml** — ターンごとの event id 索引
- **unresolved_threads.yaml** — 未解決スレッド(第1バッチではデータ形式のみ、自動運用は Phase 5)

### 5.1 State Diff 形式

```yaml
state_diff:
  id: diff_0018
  turn: 18
  changes:
    - target: character        # world | character | scene | reader_state | canon | gm_vault | relationship
      id: char_002             # target が world/reader_state 等の単一ファイルなら省略
      op: add | remove | set | delta
      path: knowledge.knows    # ドット区切り
      value: "追跡者が近づいている"   # delta の場合は数値(+8 等)
      visibility: character
      source_event: event_0081
```

- 適用はターン単位でアトミック。reject 時は状態不変。
- partial apply = changes の部分集合を選択して適用。
- 適用前 state のスナップショット(または逆 diff)を turn artifact に保存し、rollback を可能にする。

---

## 6. ターンパイプライン契約

企画書 §15.1 の 16 ステップを次の 8 フェーズに正規化する(各フェーズの入出力が turn artifact):

| # | フェーズ | 入力 | 出力 artifact |
|---|---|---|---|
| 1 | Load | project + state files | (メモリ上の TurnContext) |
| 2 | Intervene | ユーザー入力(自由文/構造化) | `intervention.yaml`(無介入なら空) |
| 3 | Simulate | world state + intervention | world 側イベント候補 |
| 4 | Act | 各キャラクターのスコープ済みコンテキスト | キャラクター行動候補(`agent_io/`) |
| 5 | Resolve | 行動候補 + イベント候補 + 乱数 | `events.yaml` + `rolls.yaml` |
| 6 | Narrate | reader可視イベントのみ | `narration.md` |
| 7 | Check | narration + events + state diff 候補 + state | `checks.yaml` |
| 8 | Commit | state diff 候補(BuildDiff 出力)+ Check 結果 | `state_diff.yaml` の apply または review 待ち |

- turn artifact ディレクトリ: `workspace/runs/turn_NNNN/` に上記 + `meta.yaml`
  (`status`、フェーズ別所要時間、LLM 呼び出し回数、`llm_tokens_total`(取得可能分の合計、取得不能時省略)、model、prompt hash、`rng_draws_consumed`(そのターンで消費した draw 数)、pipeline version)。meta.yaml は完了マーカーとして最後に書く(D111)。
- Simulate / Act / Resolve / **BuildDiff** / Check の5つがレジストリ差し替え可能なスロット(D108/D113)。BuildDiff は resolved events + interventions から state diff 候補を生成する(agent-runtime の State Manager が本実装。reveal_control の must-not-reveal 遵守は BuildDiff 契約に含まれる)。BuildDiff は Narrate 完了後・Check 開始前に実行され、`state_diff.yaml`(候補)はこの時点で書き出される — Check(consistency-checks)は diff 候補を検査対象に含むため、BuildDiff を Check の後に回してはならない。Commit はスロットではなく固定ロジック(生成済みの BuildDiff 出力を Check 結果と commit-mode に従って state-model の apply へ渡す)。
- **artifact は失敗時も必ず途中まで保存する**(partial artifact)。
- 失敗ポリシー: schema 不一致 → 最大2回 retry(llm-provider 層)→ 枯渇時はターンを `failed` として記録(D110。`stopped_for_review` は「diff 生成済み・未適用」状態専用)。
  checker が error 級を検出 → auto 進行中でも停止。決して黙って握り潰さない。
- `failed` ターンの再試行および rerun_turn は、旧 artifact ディレクトリを `turn_NNNN_discarded_<n>` へ退避してから新規ディレクトリで実行する(上書き禁止・監査可能性維持。RNG 消費数の累積は退避分も合算。D112)。

---

## 7. 乱数契約

- プロジェクトの `random_seed` から決定的 RNG を初期化。roll ごとに通番(sequence)を記録。
- 同一 seed + 同一介入列 + mock provider ⇒ 完全再現(回帰テストの基盤)。
- ダイス記法 `NdM(+/-K)`、確率判定(base_chance + modifiers → final_chance vs roll)、weighted table。
- 全 roll は `rolls.yaml` に保存(type/dice/target/modifiers/result/outcome/consequences)。
- GM override / reroll は新しい roll レコードとして追記(履歴を上書きしない)。

---

## 8. LLM 契約

- Provider interface: `complete(messages, response_schema) -> validated object`。
- 複数プロファイル(D122): 1ターン内で複数の provider/model インスタンスを同時に利用できる。呼び出し側は binding key でプロファイルを解決し、呼び出しメタデータにプロファイル名・model を記録する(meta.yaml は呼び出しごとの model を保持)。mock provider の決定性はプロファイルが異なっても保たれる。
- 全 agent 出力は Pydantic スキーマに準拠した構造化出力。検証失敗 → 修正指示付き retry(最大2回)→ 枯渇時は型付き例外を送出し、turn-pipeline がターンを `failed` として記録する(D110)。
- Mock provider: seed 決定的・スキーマ準拠の応答を返す。全テスト・smoke test は mock で実行可能でなければならない。
- API キーは環境変数のみ。ログ・artifact・例外メッセージに秘密情報を出さない。
- prompt は artifact に hash + テンプレート名で記録(全文保存はオプション、既定 on。秘匿情報を含むため workspace は private 前提)。

---

## 9. 決定ログ(D1xx = 本仕様策定時の決定)

| ID | 決定 | 理由 |
|---|---|---|
| D001-D005 | 企画書 Appendix F の通り | 状態ファースト、介入の構造化保存、ローカルファースト等 |
| D101 | 第1バッチは CLI のみ、Web UI は第2バッチ | MVP 成功条件は CLI で満たせる。UI は体験磨き込みフェーズで |
| D102 | CLI framework は typer | サブコマンド構成・型ヒント親和性 |
| D103 | 状態の正本はファイル(YAML)。SQLite は導入しない(将来も派生インデックスとして) | 人間可読・git 差分・rollback 容易。DB 二重正本は整合性リスク |
| D104 | LLM client は openai SDK + base_url 切替。LiteLLM 不採用 | 1実装で OpenAI互換/Ollama/LM Studio を賄える。依存最小化 |
| D105 | スキーマ正本は Pydantic v2 モデル | YAML/JSON 検証・構造化出力・ドキュメント生成を一元化 |
| D106 | 物語コンテンツは日本語ファースト、`project.yaml` の `language` で切替 | 企画書サンプルが日本語。コード・スキーマは英語 |
| D107 | state 変更は全て state diff 経由(直接書き換え禁止。God Mode も diff を発行) | 監査可能性・rollback・review の一貫性 |
| D108 | 拡張点は Protocol + レジストリ(provider/renderer/exporter/checker) | Phase 4+ の plugin 化に備えるが、第1バッチではレジストリ辞書のみ(plugin loader は作らない) |
| D109 | unresolved_threads / branch はデータ形式のみ第1バッチで定義、運用機能は Phase 5 | 前方互換のため形式だけ先に固定 |
| D110 | LLM 構造化出力の retry 枯渇はターン `failed`。`stopped_for_review` は「diff 生成済み・未適用」専用 | ステータスの意味論を一貫させる。Act 失敗時点では diff が存在しない |
| D111 | meta.yaml に `status` / `llm_tokens_total` / `rng_draws_consumed` を含め、完了マーカーとして最後に書く | ステータス永続化先の一元化、コスト追跡(企画書§24.4)、resume の RNG 再構築 |
| D112 | failed 再試行 / rerun_turn は旧 artifact を `turn_NNNN_discarded_<n>` へ退避(上書き禁止) | 監査可能性。rolls.yaml の新旧混在を防ぐ。RNG 累積は退避分も合算 |
| D113 | BuildDiff を5番目のスロットとし、State Manager がその実装。Commit は固定ロジック | State Manager と Commit の二重 diff 生成を排除。reveal_control の強制点を BuildDiff 契約に一本化 |
| D114 | 介入タイプ×user_mode 権限マトリクスの正本は session-autonomy。intervention は普遍不変条件(canon_edit/hidden_truth_edit→full_gm/god)+プラガブル判定(既定許可)のみ | 権限の意味情報は企画書§8(モード定義)由来であり session-autonomy の責務。DAG 順序とも整合 |
| D115 | Scene.hidden_facts は構造化(id=fact_NNN, text, visibility, known_by)。reader_visible_facts は list[str] のまま | per-fact スコープがないと §4.3 不変条件(本人が見てよい hidden_facts)が実装不能 |
| D116 | relationship の対象特定は複合キー `<from_id>__<to_id>`(独自 id なし) | ペアが自然キー。二重 id による重複リスク回避 |
| D117 | 必須7 state ファイルの欠落は StateStore.load でも fail-fast(空ファイルは空コレクション) | init が必ず生成する以上、欠落=壊れた workspace。「黙って握り潰さない」原則 |
| D118 | commit-mode は turn 実行 API のランタイムパラメータ(project.yaml に入れない)。`llm.timeout_seconds`/`llm.prompt_recording` は project.yaml `llm` に正式追加 | commit-mode は session-autonomy が置換する暫定物でありスキーマ汚染を避ける。timeout 等はプロジェクト毎の永続設定 |
| D119 | stop_condition 介入は10番目の停止条件として配線し、全 autonomy レベル(watch/god 含む)で停止する | ユーザーの明示的停止要求を黙って無視しない(D107 と同精神) |
| D120 | reject_all ターンの narration は artifact として保持するが、export-replay の正史からは除外(review.yaml の decision を参照) | 監査可能性と読者向け正史の分離 |
| D121 | Conflict Resolver は検出した衝突を例外なく roll で解決(決定的除外ルールは将来拡張)。Event は任意の `roll_ids` を持ち、export の roll 可視性はそれを参照する reader 可視イベントから導出 | バッチ1の単純化・決定的テスト。roll 自体に visibility を持たせない |
| D122 | LLM は名前付きプロファイル(`llm_profiles`)+ binding(`llm_bindings`)でエージェント種別・キャラクター単位に切替可能。`llm` は既定プロファイル。1ターン内の複数 provider 同時利用を正式サポート | ユーザー要件(キャラクターごと・進行役ごとに異なる LLM)。企画書 §24.4 の small/large モデル役割分担にも接続 |
| D123 | `CharacterState.status`(alive/dead/missing)、`SceneState.status`(active/ended)、Roll の任意 `severity`(normal/critical)を追加し、停止条件(character_death/scene_end/heavy_roll_failure)を機械的に評価可能にする。severity は Conflict Resolver が明示指定、random-engine は自動判定しない | PR #11 Codexレビュー指摘: 判定材料が無いと停止条件が「推測または絶対に発火しない」実装になる |

## 10. 未決事項(ユーザー確認待ち・第1バッチをブロックしない)

- Web UI 技術(HTMX vs React)— Phase 4 proposal 時に決定
- 実LLM の既定 provider/model(開発は mock、動作確認用の推奨構成のみ README に記載)
- fanfiction mode / raw text 非保持モードの詳細 — Phase 6+
