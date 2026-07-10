# E7〜E9 実装計画DAG(2026-07-11確定)

対象: `feature-dag.md` のE7(Game)/E8(Visual)/E9(Productization)エピックをissue粒度に分解。project_plan §11/§17/§20 とコード拡張点調査(2026-07-11)に基づく。進め方はG2ループ(ADR-0001)のまま: issue → coder委任(worktree並列) → verifier → detect_changes → commit。issue番号がDAGノードID(031〜050)。

---

## 事前決定(実装を止めないための先回り判断 — 着手時にADR化)

| # | 決定 | 根拠 |
|---|---|---|
| D-1 | E7/E8の拡張点は**既存レジストリをそのまま使う**: `pipeline/registry.py` SlotRegistry、`safety/registry.py` CHECKERS、`narration/renderers.py` RendererRegistry、`llm/registry.py` 同型のprovider dict。plugin SDK(049)は後追い形式化 — SDK完成を待たない | project_plan §11.3の10 plugin点はD108レジストリで満たせる。依存逆転(Phase 9がPhase 7/8の土台)を解消 |
| D-2 | stats/skills/inventoryは `CharacterState` へ**正フィールド追加**(`extra=allow` に逃げない)。`schema_export.SCHEMA_MODELS` 更新必須 | D105: Pydanticがスキーマの単一正本 |
| D-3 | 戦闘は**resolveスロット拡張**で実装。新パイプラインフェーズは追加しない。`conflict_resolver.py` の効果機構(`_roll`/`exclusive`/`life_or_death`)が既存の縫い目 | §20「簡易戦闘」のみ。8フェーズ構造(spec-foundation §6)不変 |
| D-4 | 画像/音声は**プロンプト生成+Providerインターフェース**のみ。エンジン内生成なし。権利注意書きはUI・export両方に必須 | §11.6 / §24.5(権利リスク明示)。生成はprovider委譲 |
| D-5 | `ProjectConfig` に `schema_version` を**最初に追加**(044)。現状versionフィールド無し(`pipeline/version.py` のPIPELINE_VERSIONのみ) | 以後の全schema変更のmigration基盤。後付けは全プロジェクト破壊的 |
| D-6 | 費用追跡は既存 `CallMetadata` → `meta.yaml`(`llm_tokens_total`/`llm_calls`)の**集計のみ**。新計測は作らない | `llm/metadata.py` / `pipeline/writer.py:110` に計測済み |
| D-7 | マルチユーザー/オンラインTRPGは非目標のまま(§6)。telemetryはoptional・ローカルのみ(§20) | 企画書の明示制約 |

## Track D: E7 Game Extension(state核共有 — レーン内直列)

| # | 機能 | スペック要旨 | 依存 |
|---|---|---|---|
| **031** | stats/skills schema | `CharacterState` に `stats`/`skills` 正フィールド(D-2)。schema_export登録、mist_stationテンプレ反映、character sheet表示(status CLI + web GM pane) | 044(schema_version先行) |
| **032** | 判定ルール(skill check) | stats/skillsを修正値にした判定(`roll_chance` + modifiers、§5.3)。判定難易度(target)表現。介入 `dice_roll_request` 経路から要求可能に | 031 |
| **033** | inventory runtime | `inventory: list[str]` を構造化(id/name/qty)へ。取得/使用/喪失をdiff化(state_manager経路、faction_move同型) | 031 |
| **034** | quest runtime | Quest model(id/status/objectives)。thread台帳(014)同型のopen/advance/resolve。narrator文脈供給 | 033 |
| **035** | PC参加モード配線 | `UserMode.PLAYER_CHARACTER`・`player_char_id` は既存。PC発言/行動入力/判定要求/所持品使用をturnフローへ配線。PC視点scope(自キャラ情報のみ、§4準拠) | 032, 033 |
| **036** | encounter table | `select_weighted` 既存流用。world simulatorのイベント誘発に接続、テンプレに `encounters.yaml`(optional load) | 031 |
| **037** | 簡易戦闘 | resolveスロット拡張(D-3): HP=stats内、戦闘=イベント+roll列。重大失敗はstop condition連動(§10.6) | 032 |
| **038** | TRPGセッションモード+ゲート | PC+判定+戦闘+クエストの通し確認。`trpg.py` exporterへ戦闘/クエスト織込み。**019 benchへgame系メトリクス追加 = E7品質ゲート** | 034, 035, 036, 037 |

## Track E: E8 Visual/Media(export/renderer系 — 040以降はTrack Dと並列可)

| # | 機能 | スペック要旨 | 依存 |
|---|---|---|---|
| **039** | visual profile schema | キャラ外見プロファイル+背景プロファイル+画風固定(§17.5)。schema_export登録 | 044(+031とstate/models.py競合 — 直列) |
| **040** | image prompt generator | シーン毎画像プロンプト生成(LLM補助、visual profile参照で外見一貫性)。`export_replay/` に新exporter + CLI subcommand | 039 |
| **041** | image provider interface + cache | Provider Protocol + dict registry(`llm/registry.py` 同型)。生成履歴・採用/破棄・asset cache。**権利注意書き必須**(D-4) | 040 |
| **042** | VNレンダラ+VN script export | RendererRegistryに `vn` 登録。台詞ウィンドウ/立ち絵指定/背景/BGM指示のscript形式(§17.4)。exporter追加 | 039 |
| **043** | voice/TTSプロンプトexport | ナレーション/台詞の読み上げ台本。TTS provider interface(041同型) | 042 |

## Track F: E9 Productization

| # | 機能 | スペック要旨 | 依存 |
|---|---|---|---|
| **044** | schema_version + migration骨格 | `ProjectConfig.schema_version` 追加、loader検査、migration registry(N→N+1関数)。**全トラックの最優先・最初に実施**(D-5) | なし(**ready**) |
| **045** | cost tracking | `meta.yaml` の `llm_tokens_total`/`llm_calls` 集計(status CLI + web pane)。モデル別価格テーブル(D-6) | なし(D/Eと並列可) |
| **046** | settings UI + model profile UI | web設定ページ(LLM profiles/bindings閲覧・編集)。localhost bind固定維持(テスト保証済み前提) | 045 |
| **047** | backup/restore | `copy_project_for_branch`(session/rollback.py)をbackup primitiveに昇格。`living-narrative backup/restore` CLI | 044 |
| **048** | Docker Compose + quickstart | compose.yml、README quickstart(「READMEだけで起動」が受入条件) | 046 |
| **049** | plugin SDK形式化 | 既存レジストリ群をentry-points group(`[project.entry-points]` 新設)で外部登録可能に。plugin sandbox方針はADR。**着手前に /security-review 必須** | 038, 043(登録面が出揃ってから) |
| **050** | sample worlds + docs仕上げ | mist_station以外のサンプル世界1〜2、権利・セキュリティ注意書きdocs整備 | 048 |

## DAG

```mermaid
graph TD
  044[044 schema_version] --> 031[031 stats/skills]
  044 --> 039[039 visual profile]
  044 --> 047[047 backup/restore]
  subgraph TrackD[Track D: E7 Game]
    031 --> 032[032 判定ルール]
    031 --> 033[033 inventory]
    031 --> 036[036 encounter]
    033 --> 034[034 quest]
    032 --> 035[035 PC参加]
    033 --> 035
    032 --> 037[037 簡易戦闘]
    034 --> 038[038 TRPGモード+ゲート]
    035 --> 038
    036 --> 038
    037 --> 038
  end
  subgraph TrackE[Track E: E8 Visual]
    031 -. state/models.py競合 .-> 039
    039 --> 040[040 image prompt]
    040 --> 041[041 provider+cache]
    039 --> 042[042 VNレンダラ]
    042 --> 043[043 TTS]
  end
  subgraph TrackF[Track F: E9 Product]
    045[045 cost tracking] --> 046[046 settings UI]
    046 --> 048[048 Docker+quickstart]
    048 --> 050[050 samples+docs]
  end
  038 --> 049[049 plugin SDK]
  043 --> 049
```

**readyノード**: 044(最優先)、045。044完了後: 031、039(031と直列)、047。

## レーン並列と競合

- **Track D内は直列**(`state/models.py`・`state_manager.py` 共有)
- **039は031と直列**(両方 `state/models.py` に触る)。040以降(export/renderer系)はTrack Dと**worktree並列可**
- **045/046はD/Eと並列可**(`web/`・集計系、state核に触らない)
- 1 issue = 1 commit = 1 worktree。issueファイルは着手時に `docs/issues/NNN-slug.md` へ詳細化(このdocの行がスペック源)

## 詰まり防止チェックリスト(worktree worker運用 — 017の実績から)

1. worktree作成後、workerに **`uv sync --extra web` を最初に実行させる**(017でtest収集エラー誤診断 → 無関係ファイル改変の原因になった)
2. テスト計数は `NO_COLOR=1 uv run pytest` か `./.venv/bin/pytest -q`(rtk 0.43.0のANSIパーサバグで誤計数)
3. coordinator側: merge/push前に `git branch --show-current` で現在地確認(cwd不整合でworktree内push事故の前例)
4. dispatchプロンプトに毎回明記: 「ドキュメント・issueは日本語第一(D106)」「無関係ファイル変更禁止」「環境エラーはコード改変でなく環境側で直す」
5. commit前 `detect_changes`、GitNexus reindexはバッチ毎にまとめて実行
6. 実LLMスモークは `sandbox/` + OmniRoute(`auto/best-coding`)8〜12ターン。テンプレート改変で誘発しない(パラメータはsandbox側で改変)

## ゲート

- **E7ゲート**: 038で019 regression benchにgame系メトリクスを追加して通過
- **E9ゲート**: 049着手前に `/security-review`(plugin実行面)、E9完了条件はproject_plan §20 Phase 9(READMEだけで起動/backup・restore/migration/plugin追加方法/権利・セキュリティ明記)
- **権利注意書き**: 041(画像)・043(音声)のexport物とUIに必須(§11.6、§24.5)

## 推奨順序

044 → (045並走) → 031 → 032/033 → 039(直列挿入)→ 以降D/E並列 → 038ゲート → 049 → 048/050

現在地（2026-07-11）: Issue 038のmock統合・50ターンbench・実LLM 8ターンスモークがすべてgreenとなり、E7ゲートを通過した。
