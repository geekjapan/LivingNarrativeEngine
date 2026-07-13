# UX受入チェックリストと人手smoke手順

## 目的と適用範囲

この文書は、[Issue 058](issues/058-v1-ux-gate.md)で承認された1.0 UX gateを、
人手で再実行できるチェックリストと記録形式へ固定する。対象personaは、
[ADR-0005](adr/0005-v1-release-contract.md)の「自分のPCへ導入し、Web UIで一人遊び
する物語シミュレーション愛好者」である。

1.0のUX受入は、次の2セッションを同じリリース候補で実施して判定する。

1. **Session 1 — clean新規journey**: 新規projectを作成し、代表journeyを最初から最後
   まで通す。
2. **Session 2 — 既存継続+復旧**: 既存projectを開き、継続、失敗からの復旧、
   backup/restore後の再開を通す。

この文書は[β/1.0人手品質rubric](beta-quality-gate-rubric.md)の代替ではない。
β/1.0の物語品質はIssue 073のR1–R8、UXはこの文書のU/M/R/I/Aをそれぞれ判定する。
評価記録には秘密値、credential、`gm_vault`本文、`hidden_facts`本文、character secret、
`private_mind`を記録しない。

## 対応面と判定ルール

058の決定に従い、WebとCLIの責務を次のように固定する。

| 面 | 1.0で確認する機能 | 判定経路 |
|---|---|---|
| Web必須 | 観測、複数turn、auto、介入、review 3決定、停止/再開、disclosure gate | Web UIで操作し、reader-visible応答を確認 |
| CLI必須・Web任意 | `init`、`export`、`backup` | CLIで完遂し、Webの案内から導線を発見 |
| CLI必須（片方でよい） | `edit`、`rerun_turn`、`rollback`、`branch` | UX受入の必須journeyには含めず、CLI導線の存在だけ確認 |
| 片方でよい | 設定編集 | WebまたはCLIのどちらかで完遂 |

各セッションの必須stepは、補助なしで1回成功、ヘルプ参照はstepあたり1回以下、
詰まり0件とする。`N/A`、未記録、証跡なしはその項目の`NO`である。セッションの
合否は、必須stepとU/M/R/I/Aの全項目が`YES`のときだけ`PASS`とする。

## 観察項目合否表

| ID | 観察項目 | `YES`の条件 | 証跡 |
|---|---|---|---|
| U | task completion | 各必須stepを補助なしで1回成功し、stepごとのヘルプ参照が1回以下、詰まりが0件 | step記録、所要秒、ヘルプ回数 |
| M | 誤操作 | disposable projectで誤った破壊的操作を1回行っても、turn/review等のartifactが残り、正本stateが意図せず変更されない | 操作前後のstatus、artifact path、state比較 |
| R | 復旧 | `failed` turn後にUIが操作不能にならず、次のturn/reviewへ復帰できる。またbackup→破壊→restoreを1回通し、restore後に継続できる | failed/meta、review結果、backup manifest、restore後turn |
| I | 情報scope | reader-visibleなWeb全応答で`gm_vault`、`hidden_facts`、secrets、`private_mind`のmarkerと本文のleakが0件。`player_character`ではsensitive/GM routeが全て403 | Issue 075のscan/403 test、対象runのURLと結果 |
| A | accessibility | マウスを使わず必須Web journeyを完遂し、通常テキストのコントラストが4.5:1以上で、全controlに可視labelまたはaccessible nameがある | キー操作記録、コントラスト測定、control一覧 |

WCAG全面準拠はこのgateの目標ではない。panel toggleのfocus復帰は`should`として
観察・記録するが、058の必須判定とは別に扱う。

## 事前準備と共通記録

評価者は実行前に、次を固定する。

- 評価ID、gate（`beta`または`1.0`）、git revision、実施日時、評価者、OS、ブラウザ。
- install経路（uvまたはDocker）、project template、provider/model。credentialは値を
  書かず、provider名とmodel名だけを記録する。
- Session 1はfresh venvまたは新規Docker imageなどのclean install環境と、空の一時出力先を
  使う。既存の依存環境を使った場合はinstall stepを`NO`とする。
- Session 1は空の一時ディレクトリ、Session 2は既存projectの複製を使う。実運用の
  projectや復元元を直接破壊しない。
- Web serverをlocalhostで起動し、ブラウザからprojectを選択できることを確認する。
- 失敗を意図的に起こす場合は、使い捨てprojectのproviderを一時的に到達不能な
  localhost endpointへ変更する。実credentialや外部サービスを壊す方法は使わない。
- 記録に残すpathは`projects/`または`sandbox/`からの相対pathとし、秘密を含む絶対pathや
  URL queryを保存しない。

初回起動の標準形は次のとおりである。実際の出力先だけ評価記録の値へ置き換える。

```bash
uv sync --extra web
uv run living-narrative init \
  --title 'UX acceptance' \
  --template mist_station \
  --output sandbox/ux-acceptance
uv run living-narrative serve --project-root sandbox
```

`serve`は別プロセスで起動し、評価後に停止する。export/backupの引数はWebの案内または
`--help`で確認し、実行した完全なコマンドと生成artifactの相対pathを記録する。

## Session 1 — clean新規journey

### 事前条件

- 空の一時出力先で`init`が成功し、`project.yaml`とworkspaceが作成されている。
- Web画面にprojectが表示され、空状態では`living-narrative init`の案内が見える。
- 記録開始時刻を固定し、ブラウザを再読み込みしてから測定する。

### 手順

| Step | 操作 | 成功条件 |
|---|---|---|
| S1-1 | installとCLI起動 | installが完了し、CLIのhelpまたは`init`を起動できる |
| S1-2 | CLI `init` | 新規projectが作成され、Webのproject選択に現れる |
| S1-3 | `serve`起動とWeb接続 | Web UIを開き、projectを選択でき、export/backupのCLI導線が見える |
| S1-4 | 初期状態の観測 | status、登場人物、storyが読み取れ、GM viewはreader viewと混ざらない |
| S1-5 | 複数turnとauto | 次のturnを実行し、autoでも複数turnを進め、進行状況を確認できる |
| S1-6 | 自由文介入 | 自由文を入力して次のturnを進め、介入履歴と結果を確認できる |
| S1-7 | 構造化介入 | type、target、content、visibilityを入力して次のturnを進められる |
| S1-8a | review `accept_all` | review待ちのdiffを確認し、全変更を適用して次へ進める |
| S1-8b | review `reject_all` | review待ちのdiffを確認し、正本stateを変更せずに次へ進める |
| S1-8c | review `partial` | 変更を1つ以上選択して適用し、選択結果だけが正本へ反映される |
| S1-8d | 誤操作の確認 | disposable projectで意図した変更とは異なる`reject_all`を1回実行しても、artifactが残り、正本stateが意図せず変更されない |
| S1-9 | 停止と再開 | autoを停止し、画面を再読み込みまたは次のturn操作で同じprojectを再開できる |
| S1-10 | CLI `export` | Web上のCLI導線を発見し、export artifactを生成できる |

review 3決定は、review待ちを作れるまでturnを進め、`accept_all`、`reject_all`、
`partial`をそれぞれ1回ずつ使う。reviewが発生しない場合は、該当stepを`N/A`にせず
`NO`とし、使用したautonomy設定とturn statusを記録する。

S1-4からS1-9は、同じWeb画面でキーボードだけを使って再実施する。Tab順、focusの
可視性、Enter/Spaceによる操作、statusの更新を記録する。コントラストは通常テキスト
（4.5:1以上）と、実際に使用するcontrolの文字・背景色を測定する。

## Session 2 — 既存継続+復旧

### 事前条件

- Session 1または固定fixtureから、少なくとも1 applied turnがあるprojectを複製する。
- 複製直後にbackupを作成し、backup rootと`manifest.yaml`のpathを記録する。
- 復旧操作の前後で比較できるよう、current turn、reader-visible story、主要stateの
  checksumまたは差分を記録する。

### 手順

| Step | 操作 | 成功条件 |
|---|---|---|
| S2-1 | 既存projectをWebで開く | 過去turnと現在statusが表示され、前回の状態から続行できる |
| S2-2 | 継続turn | 1つ以上turnを進め、既存storyと新しい結果が連続している |
| S2-3 | controlled failure | disposable projectでprovider failureを起こし、turnが`failed`として記録される。stateが途中適用されない |
| S2-4 | failed後の復帰 | 有効なproviderへ戻し、次のturnを実行する。review待ちになった場合はWeb reviewを開き、決定後に継続できる |
| S2-5 | backup→破壊 | 複製projectの一部artifactを削除または変更する。元projectとbackupは変更しない |
| S2-6 | restore | backupを新しい空directoryへrestoreし、manifestのschema versionと復元結果を確認する |
| S2-7 | restore後の再開 | restore先projectをWebまたはCLIで開き、turnを続行できる。復元前の正本と意図しない差分がない |
| S2-8 | scope/a11y再確認 | reader view、player modeの403、キーボード操作、control label、contrastを再確認する |

S2-3で失敗turnの原因とturn番号を記録する。失敗を`accept`や再試行で消してはならず、
失敗artifactが残ったまま、次の有効なturnへ復帰できたことを証跡にする。S2-5の「破壊」は
復元先を作るための制御された変更に限り、実運用projectの削除や上書きは行わない。

## 記録テンプレート

各セッションで次のテンプレートをコピーする。`YES`の根拠は、短い事実、turn番号、
artifact pathまたは測定値で記録する。

```markdown
# UX受入評価 — <evaluation-id>

- gate: beta | 1.0
- session: 1-clean-new | 2-existing-recovery
- result: PASS | FAIL
- evaluated_at: <ISO-8601>
- reviewer: <name>
- git_revision: <commit>
- os_browser: <OS / browser>
- install_path: uv | docker
- template: <template>
- provider: <provider, no credential>
- model: <model>
- project: <relative sandbox/projects path>
- started_at: <ISO-8601>
- finished_at: <ISO-8601>

## Step記録

| Step | Y/N | seconds | help_count | stuck | recovery | evidence | notes |
|---|---|---:|---:|---|---|---|---|
| S1-1 or S2-1 | Y/N | <sec> | <n> | 0 or 1 | Y/N | <relative path> | <fact> |

## 観察項目

| ID | Y/N | 根拠 | notes |
|---|---|---|---|
| U task completion | Y/N | <step IDs and evidence> | <fact> |
| M 誤操作 | Y/N | <before/after artifact or diff> | <fact> |
| R 復旧 | Y/N | <failed/review/backup/restore evidence> | <fact> |
| I 情報scope | Y/N | <scan/403 evidence> | <marker名やsecret本文は書かない> |
| A accessibility | Y/N | <keyboard, labels, contrast ratio> | <fact> |

## 補足

- panel_toggle_focus: PASS | ISSUE | NOT_TESTED (should)
- failed_turn: none | turn <N>, <short non-secret reason>
- backup_root: <relative path>
- restore_root: <relative path>
- failed_items: <none or IDs>
- notes: <再現に必要な最小限の補足>
```

セッションの`result`は、必須stepが全て`Y`で、U/M/R/I/Aが全て`Y`のときだけ`PASS`と
する。片方のセッションが`FAIL`なら1.0 UX gateは`FAIL`である。

## β人手smokeへの流用

βでは、この文書の**Session 1を1回だけ**実施し、その記録をβのUX journey証跡として
流用する。実施時は次を満たす。

1. ADR-0005 D4に従い、βの代表journeyは実LLMで実行する。provider failure、途中停止、
   turn欠落があれば、UX記録も`FAIL`とする。
2. Session 1の記録に加えて、[Issue 073のrubric](beta-quality-gate-rubric.md)を同じ
   runのartifactへ適用する。R1–R8の`PASS`はUXのU/M/R/I/Aの`PASS`を自動的には代用しない。
3. Issue 072のbenchmark JSON/Markdown、UX記録、Issue 073のhuman-rubric記録を同じ
   `run_id`または相互参照できる評価IDで保存する。
4. βのSession 1は「新規projectを作成してWebで観測・複数turn・介入・review・停止/再開・
   CLI exportまで通す」ことを記録し、backup/restoreの補助journeyはβの必須stepにしない。

βの1回のsmokeは、1.0の2セッション完了を意味しない。1.0 gateではリリース候補で
Session 1とSession 2を実施し、両方の記録を揃える。β記録を1.0へ再利用する場合も、
git revision、provider/model、環境、artifactが同一であることを確認し、変更後は再実施する。
