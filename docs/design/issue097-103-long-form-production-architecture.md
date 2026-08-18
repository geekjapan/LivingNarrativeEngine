# LivingNarrativeEngine: Issue 097〜103 設計・運用ガイド

**対象コミット:** `47d1a5d`（2026-08-18）
**対象範囲:** revision lineage、continuity、circuit breaker、Web Cockpit、accepted manuscript export、長編benchmark

## 1. Issue 103: 長編benchmark harnessの実行方法

### 1.1 目的と入力境界

`benchmark_book()` は、**workspaceを変更せず**に `state/` の `BookPlanState`・`BookLedgerState` と、`books/chapters/` 配下のimmutable lineageを読み取ります。出力には本文、prompt、認証情報、絶対パスを含めません。そのため、CI artifactや複数の制作runの比較に使用できます。

> 現時点のIssue 103は、制作進捗とartifact同一性を測定する決定的な**観測ハーネス**です。章本文の商業品質を自動採点する評価器や、実LLMを使う30〜200章の負荷実験を自動実行するオーケストレータではありません。

| 入力 | 読み取る内容 | 出力への反映 |
|---|---|---|
| `workspace/state` | BookPlan、章lifecycle、continuity ledger | 章数、accepted/revising/block中章数、open thread数 |
| `workspace/books/chapters` | `ChapterLineage`内のcandidate SHA-256 | attempt数、artifact fingerprint |
| 呼出し側のラベル | 比較対象を識別する名前 | `name` |

### 1.2 単一Bookの実行

現状はCLI subcommandではなく、Python APIとして公開しています。次のスクリプトをリポジトリ直下に例えば `scripts/run_book_benchmark.py` として保存し、`uv run python scripts/run_book_benchmark.py` を実行してください。

```python
from pathlib import Path

from living_narrative.book.benchmark import (
    benchmark_book,
    write_book_benchmark_report,
)

workspace = Path("sandbox/transmigrated-crown/project/workspace")
observation = benchmark_book(workspace, name="transmigrated-crown")
report_path = write_book_benchmark_report(
    Path("sandbox/transmigrated-crown/benchmark-report.json"),
    [observation],
)
print(report_path)
```

出力先ディレクトリは自動作成され、reportは一時ファイルへの書込み、`fsync`、原子的renameで確定します。途中停止時に破損したJSONが完成ファイルとして残ることを防ぎます。

### 1.3 複数Bookの比較

比較対象ごとに一意の `name` を設定します。同じ名前を二度渡すと、比較の曖昧性を防ぐため `ValueError` になります。

```python
observations = [
    benchmark_book(Path("fixtures/fantasy-a/workspace"), name="fantasy-a"),
    benchmark_book(Path("fixtures/fantasy-b/workspace"), name="fantasy-b"),
]
write_book_benchmark_report(Path("artifacts/book-benchmark.json"), observations)
```

### 1.4 実測レポート例

`transmigrated-crown` sandboxに対する実行結果は次のとおりです。

```json
{
  "books": [
    {
      "accepted_chapters": 1,
      "artifact_fingerprint": "b8657464c29745d53e330a9bd3aa54c8f1868449b46077dfef4b3d25e1d69621",
      "attempt_count": 0,
      "blocked_chapters": 0,
      "name": "transmigrated-crown",
      "open_thread_count": 0,
      "planned_chapters": 9,
      "revising_chapters": 0
    }
  ],
  "schema_version": 1
}
```

このsandboxでは、Issue 097導入前にaccept済みだった第1章にはimmutable attempt artifactが遡及作成されていないため、`accepted_chapters` は1、`attempt_count` は0です。これはbenchmarkの欠損ではなく、**legacy accepted artifactを捏造せず、lineageの実在だけを測定する**正本方針の結果です。以後、`record_chapter_candidate()` を通る章はattemptとして集計されます。

### 1.5 指標の読み方

| フィールド | 意味 | 運用上の解釈 |
|---|---|---|
| `planned_chapters` | BookPlanにある全章数 | 計画のスケール |
| `accepted_chapters` | lifecycleが`accepted`の章数 | 原稿化可能な進捗 |
| `revising_chapters` | lifecycleが`revising`の章数 | 改稿backlog |
| `blocked_chapters` | `review`または`revising`の章数 | 品質ゲートで止まる制作量 |
| `attempt_count` | lineage上のimmutable candidate数 | 改稿・試行コストの代理指標 |
| `open_thread_count` | continuity ledgerの未解決thread数 | 物語上の回収負債 |
| `artifact_fingerprint` | 章順・attempt identity・accepted attemptとcandidate hashのSHA-256 | 同一入力・同一成果物の比較、回帰検知 |

`artifact_fingerprint` は本文内容を出力しません。ただし、章順、attemptの所属、accepted attempt、またはcandidate hashが変化すれば変わります。したがって、同じfixtureの二回測定でhashが異なる場合は、BookPlan順序、lineage、または保存済みattemptが変化したことを示します。

## 2. Issue 097〜103 の統合アーキテクチャ

### 2.1 正本の層と非正本の層

設計の中心は、状態遷移の正本をYAML状態とtransaction journalに置き、本文・review・promptをartifactとして分離することです。UI、export、benchmarkは正本を変更せず、原則として読取りモデルまたは明示的なcoordinator操作として働きます。

```text
Story Bible
    │
    ▼
BookPlan proposal ── apply (StateDiff + transaction) ──► BookPlanState / BookLedgerState
                                                          │
                                                          ▼
planned ── start ──► running ── candidate ──► review ── accept ──► accepted
                          │                    │             │
                          │                    │             ├─ immutable attempt pointer
                          │                    │             └─ continuity ledger更新
                          │                    ▼
                          └─ draft run artifacts       revise ──► revising ──► 次attempt
                               request/prompt/
                               response/meta/circuit-breaker

accepted attempts ──► manuscript exporter ──► manuscript.md + manifest
Book state + lineage ──► benchmark harness ──► public JSON report
Book state ──► reader-safe Cockpit projection ──► Web UI / 操作API
```

### 2.2 コンポーネント責務

| Issue | 主モジュール | 書込み境界 | 読取り境界 | 不変条件 |
|---|---|---|---|---|
| 097 | `book/lineage.py`、`book/coordinator.py` | attempt dir、chapter manifest | exporter、benchmark、coordinator | 旧attemptを上書きしない。accept pointerはaccept reviewだけを指す。 |
| 098（前提済） | `book/review.py` | review artifact | coordinator | semantic blockのreviewはacceptedへ進めない。 |
| 099 | `book/continuity.py`、`book/chapters.py` | `BookLedgerState.continuity`をStateDiff経由で更新 | draft prompt、semantic review | digestはreader-safe・上限付き。private/GM情報を混入させない。 |
| 100 | `book/budget.py`、`book/drafting.py` | `circuit_breaker.yaml` | draft preflight | provider呼出し前にattempt/revision上限を判定する。 |
| 101 | `web/service.py`、`web/app.py`、`web/page.py` | coordinatorのみがlifecycle更新 | `BookCockpit` | UIは状態を直接編集しない。権限と409競合応答を通す。 |
| 102 | `book/exporter.py`、`cli/export.py` | output dirへのatomic write | accepted lifecycle + pointer + lineage | acceptedでない章、欠落pointerをexportしない。 |
| 103 | `book/benchmark.py` | public reportへのatomic write | state + lineage | path、prompt、credential、本文をreportに含めない。 |

### 2.3 章制作のデータフロー

1. **計画確定**では、Story Bibleから作られたBookPlan proposalを`apply_book_plan_proposal()`がtransactionにより反映します。ここでBookPlanと初期BookLedgerが生成されます。
2. **開始**では、CockpitまたはCLI相当の呼出しが`start_chapter_production()`を通し、`planned → running`をjournal-before-stateで確定します。同じ開始要求は同一journalを再利用できるidempotent操作です。
3. **本文生成**では、`run_chapter_draft()`がrequest、prompt、response、metaを分けて保存します。responseが存在する再開時はproviderを再呼出ししません。budget超過ならprovider呼出し前に`circuit_breaker.yaml`を残して止まります。
4. **candidate/review登録**では、candidate本文hashをキーにartifactを保存し、Issue 097のlineageへimmutable attemptを追加します。改稿して本文が変われば新attemptになり、以前の本文・review・runを保全します。
5. **品質ゲート**では、長さなどの決定的条件に加え、required thread被覆をsemantic continuityとして評価します。block findingを持つreviewはacceptできません。
6. **accept**では、coordinatorがreview決定を再検証して`accepted`へ遷移させ、accepted attempt pointerを更新します。同時にaccepted本文からreader-safe continuity digestを導出し、BookLedgerのopen threadを更新します。
7. **消費系**では、exporterがaccepted pointerの本文だけをBookPlan順に集約し、benchmarkが状態とhashのみを集計します。どちらもcandidateの「最新版」や未accept本文を推測しません。

### 2.4 Web Cockpitの操作境界

Web UIは次の三つのmutationのみを公開し、本文や内部promptを直接書き換えません。

| UI状態 | 操作 | HTTP endpoint | coordinator遷移 |
|---|---|---|---|
| `planned` | 制作を開始 | `POST /api/project/{name}/book/chapters/{chapter_id}/start` | `planned → running` |
| `review` | 承認 | `POST /api/project/{name}/book/chapters/{chapter_id}/accept` | `review → accepted` |
| `review` | 改稿 | `POST /api/project/{name}/book/chapters/{chapter_id}/revise` | `review → revising` |

すべてのmutationはproject解決、既存のsensitive session access、coordinator、transaction lockを経由します。無効なlifecycleやreview拒否はHTTP 409として返し、UIはCockpitを再読込します。UIテンプレートへ入る外部データは`escapeHtml`でエスケープし、XSS監査テストの対象です。

## 3. 次のマイルストーン

### 3.1 優先度A: 実制作を回せる自律orchestration

| マイルストーン | 内容 | 完了判定 |
|---|---|---|
| Production Runner | `running`章のdraft、candidate、review、accept/revise判断を一つの明示的runとして束ねる | 章単位の再開・中断・retryを状態機械として操作できる。 |
| Legacy lineage backfill | 097以前のaccepted candidate/reviewを検証付きでattempt化するmigration | exportとbenchmarkでlegacy accepted章も透明に追跡できる。 |
| Book benchmark CLI/CI | `living-narrative book benchmark`、fixture matrix、artifact upload | 複数BookをCIで定期比較し、fingerprint差分を検出できる。 |

### 3.2 優先度B: 商業品質の評価・継続性

| マイルストーン | 内容 | 完了判定 |
|---|---|---|
| Semantic Gate v2 | beat coverage、視点人物、人物関係、伏線回収のevidenceベース判定 | chapter reviewが検査項目別の根拠を保持する。 |
| Hierarchical summaries | 章digestに加え、act summary・arc summary・character arc ledgerを導入 | 20〜100章でもprompt情報量が上限内で一貫する。 |
| Editorial benchmark | 固定サンプル、rubric、blind評価、改善前後比較 | 人手評価と自動指標の相関を継続追跡できる。 |

### 3.3 優先度C: 予算・出荷・運用

| マイルストーン | 内容 | 完了判定 |
|---|---|---|
| Cost Policy v2 | token/USD上限、profile別単価、章/act/book予算、soft/hard stop | 実usage metadataから費用予測・停止・警告を決定的に行う。 |
| Export adapters | Markdown正本からDOCX、EPUB、組版PDFを生成 | manifest hashを保った再現可能な配布物を生成する。 |
| Publication manifest | 原稿、cover、metadata、version、quality gate、licenseを一体化 | 「何を出荷したか」を1つのmanifestで監査できる。 |
| Persistent queue/worker | 長時間の実LLM章制作をsandbox寿命から分離 | 100章規模の予約、再開、並行度、停止が運用可能になる。 |

### 3.4 実行順の推奨

最初にProduction Runnerとlegacy lineage backfillを実装し、実際の9章sandboxを完全なattempt列にします。次にbenchmark CLI/CIを加え、変更ごとに進捗・改稿負債・fingerprintを追跡します。その後、Semantic Gate v2とhierarchical summariesを導入して20章以上の品質を安定させ、最後にCost Policy v2とpersistent workerを組み合わせて数十万文字規模の生成を運用します。

この順序により、先に「何が起きたか」をimmutable artifactとbenchmarkで観測可能にし、次に品質とコストを強めるため、原因追跡不能な自律化を避けられます。

## 4. 検証証跡

Issue 097〜103の実装を含む最終回帰は、`1107 passed / 2 skipped`（217.57秒）でした。静的検査では`ruff check .`、`ruff format --check .`、`git diff --check`を通過しています。

| コミット | 内容 |
|---|---|
| `9132a1d` | lineage、continuity、budget、accepted manuscript export |
| `7b8c3a7` | Web serviceのreview lifecycle操作 |
| `bba3bd7` | Cockpit UIのreview操作とDOM安全性 |
| `47d1a5d` | benchmark harnessとIssue完了記録 |
