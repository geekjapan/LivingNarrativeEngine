# LivingNarrativeEngine — Issue 097〜103 変更ファイル・APIリファレンス

**対象コミット:** `9132a1d`、`7b8c3a7`、`bba3bd7`、`47d1a5d`
**対象:** Issue 097〜103（semantic continuity gateはIssue 098として既存実装を前提に含む）

## 1. 全体の公開境界

| 境界 | 公開入口 | 入力 | 出力 | 正本への影響 |
|---|---|---|---|---|
| Python domain API | `living_narrative.book.*` | `Path`、Pydantic model、chapter ID | Pydantic model、例外 | coordinator/StateDiffを通す操作だけが状態を変更 |
| CLI | `living-narrative export manuscript` | `--project`、任意の`--output` | `manuscript.md`、manifest | 出力先のみを書込み。workspace stateは読取り専用 |
| HTTP read API | `GET /api/project/{name}/book/cockpit` | project name | reader-safe Cockpit JSON | 読取り専用 |
| HTTP mutation API | `POST .../start`、`accept`、`revise` | project/chapter ID | lifecycle結果JSON | service→coordinator→transaction経由 |
| Artifact API | lineage/drafting/export/benchmark | workspace/chapters root | YAML/Markdown/JSON artifact | immutable attemptまたはatomic output |

> **設計原則:** `BookPlanState`と`BookLedgerState`はYAML正本であり、状態変更はcoordinatorが`project_lock`とtransaction journalを経由して行う。Web UI、exporter、benchmarkは状態を直接編集しない。

## 2. Issue別の主要変更ファイル

### Issue 097 — Attempt ManifestとRevision Lineage

| ファイル | 主な変更 | 公開契約 |
|---|---|---|
| `src/living_narrative/book/lineage.py` | immutable candidate/review attemptとaccepted pointer | `ChapterAttempt`、`ChapterLineage`、`load_chapter_lineage()`、`record_chapter_attempt()`、`accept_chapter_attempt()` |
| `src/living_narrative/book/coordinator.py` | candidate保存時のlineage記録、accept時pointer更新 | `record_chapter_candidate()`、`accept_chapter_review()` |
| `tests/book/test_lineage.py` | append-only保存、親子関係、accept pointerの回帰 | lineage不変性の仕様テスト |
| `tests/book/test_chapter_production_coordinator.py` | lifecycleとaccepted attemptの統合 | accept後pointer更新の統合テスト |

#### データモデル

```python
class ChapterAttempt(BaseModel):
    id: str                       # attempt_001形式
    chapter_id: str               # chapter_001形式
    parent_attempt_id: str | None
    candidate_sha256: str         # 64桁hex
    source_turns: list[int]
    draft_run_id: str | None
    review: ChapterReview
    candidate_markdown: str       # durable artifactから復元

class ChapterLineage(BaseModel):
    chapter_id: str
    attempts: list[ChapterAttempt]
    accepted_attempt_id: str | None
```

#### Python API

| 関数 | シグネチャ | 成功時 | 失敗時・保証 |
|---|---|---|---|
| `load_chapter_lineage` | `(chapters_root: Path, chapter_id: str) -> ChapterLineage` | hash検証済みlineage | 本文欠落・hash不一致・chapter ID不一致は`ValueError` |
| `record_chapter_attempt` | `(chapters_root, candidate, review, *, draft_run_id=None) -> ChapterAttempt` | 新しいappend-only attempt | candidate/review ID不一致は`ValueError`、同一本文hash/既存dirは`FileExistsError` |
| `accept_chapter_attempt` | `(chapters_root, chapter_id, attempt_id) -> ChapterLineage` | `accepted_attempt_id`を更新 | 存在しないattempt、review decisionがaccept以外は`ValueError` |

#### Artifactレイアウト

```text
workspace/books/chapters/{chapter_id}/
├── lineage.yaml
└── attempts/{attempt_id}/
    ├── candidate.md
    ├── attempt.yaml
    └── review.yaml
```

`candidate.md`は本文の唯一のimmutableコピーであり、`lineage.yaml`の`candidate_sha256`とロード時に照合されます。

---

### Issue 099 — Rolling SummaryとContinuity Ledger

| ファイル | 主な変更 | 公開契約 |
|---|---|---|
| `src/living_narrative/state/models.py` | `BookLedgerState`へcontinuity schemaを追加 | `BookContinuityEntry`、`BookContinuityState`（schema名はstate models内） |
| `src/living_narrative/book/continuity.py` | accepted本文をreader-safe digestとopen threadへ投影 | `advance_continuity_ledger()`、`render_continuity_digest()` |
| `src/living_narrative/book/chapters.py` | `ChapterContext`にcontinuity digestを追加 | `build_chapter_context()` |
| `src/living_narrative/book/coordinator.py` | accept lifecycle時のledger更新 | `accept_chapter_review()`経路 |
| `src/living_narrative/book/drafting.py` / `review.py` | 同じdigestを生成・semantic reviewへ伝播 | `run_chapter_draft()`、`review_chapter()` |
| `tests/book/test_continuity.py` / `test_chapter_compilation.py` | reader-safe、上限、context投影を検証 | continuity回帰 |

#### Python API

| 関数 | シグネチャ | 契約 |
|---|---|---|
| `advance_continuity_ledger` | `(ledger, candidate, *, required_thread_ids, covered_thread_ids, max_summary_chars=...) -> BookLedgerState` | accepted candidateから一回だけentryを追加し、未被覆threadをopenとして保持。既存chapter entryは`ValueError`。 |
| `render_continuity_digest` | `(continuity, *, max_chars=4_000) -> str` | reader-safe summaryを指定上限まで連結。draft/reviewの共通入力。 |
| `build_chapter_context` | `(bundle, chapter_id) -> ChapterContext` | BookPlan/BookLedgerから章文脈とcontinuity digestをreader-safeに投影。 |

**状態境界:** digest/open threadは`BookLedgerState.continuity`に保存される。本文全文やGM/private情報をledgerへコピーしない。

---

### Issue 100 — Book BudgetとCircuit Breaker

| ファイル | 主な変更 | 公開契約 |
|---|---|---|
| `src/living_narrative/book/budget.py` | attempt・revision上限の決定的判定 | `BookBudgetPolicy`、`BudgetExceededError`、`evaluate_draft_budget()` |
| `src/living_narrative/book/drafting.py` | provider呼出し前のpreflightと停止artifact | `run_chapter_draft()`の`budget`引数 |
| `tests/book/test_budget.py` | chapter/book上限とprovider未呼出しを検証 | circuit-breaker回帰 |

#### Python API

```python
class BookBudgetPolicy(BaseModel):
    max_attempts_per_chapter: int | None = None
    max_attempts_per_book: int | None = None
    max_consecutive_revisions: int | None = None

class BudgetExceededError(RuntimeError):
    pass

# 文字列の停止理由、または許可時はNoneを返す
evaluate_draft_budget(runs_root: Path, chapter_id: str, attempt: int,
                      policy: BookBudgetPolicy) -> str | None
```

`run_chapter_draft(..., budget=BookBudgetPolicy(...))`はpreflightで超過を検出すると`BudgetExceededError`を送出し、draft run配下へ`circuit_breaker.yaml`を保存します。providerは呼び出されません。

**現時点の範囲:** attempt数・連続改稿数のhard stopを実装済みです。token/USD上限は既存のusage集計に重ねる後続拡張です。

---

### Issue 101 — 長編制作Web Cockpit

| ファイル | 主な変更 | 公開契約 |
|---|---|---|
| `src/living_narrative/book/cockpit.py` | reader-safe Cockpit read model | `BookCockpit`、`build_book_cockpit()` |
| `src/living_narrative/web/service.py` | FastAPI非依存のuse case | `get_book_cockpit()`、`start_book_chapter()`、`accept_book_chapter()`、`revise_book_chapter()` |
| `src/living_narrative/web/app.py` | Cockpit read/mutation routes | 下表のHTTP endpoint |
| `src/living_narrative/web/page.py` | roadmap、状態badge、開始/承認/改稿のUI | vanilla JavaScriptのfetch操作 |
| `tests/web/test_book_cockpit_api.py` / `test_web_app.py` | HTTP契約、idempotence、DOM安全性 | Web回帰 |

#### HTTP API

| Method / path | 成功応答 | 失敗応答・セキュリティ |
|---|---|---|
| `GET /api/project/{name}/book/cockpit` | `BookCockpit`のJSON。premise、next action、章ごとのID/act/lifecycle/goal/word range | project不在は404。sensitive session access必須。 |
| `POST /api/project/{name}/book/chapters/{chapter_id}/start` | `{"chapter_id": "...", "lifecycle": "running", "journal_id": "..."}` | lifecycle不正・lock競合は409。再送は同一journalを再利用可能。絶対パスは返さない。 |
| `POST /api/project/{name}/book/chapters/{chapter_id}/accept` | `{"chapter_id": "...", "lifecycle": "accepted"}` | lock・不正lifecycle・reject review・semantic blockは409。 |
| `POST /api/project/{name}/book/chapters/{chapter_id}/revise` | `{"chapter_id": "...", "lifecycle": "revising"}` | lock・不正lifecycleは409。 |

UIから状態YAMLを直接更新する経路はありません。全mutationは`web.app → web.service → coordinator → project_lock + transaction`を通ります。

---

### Issue 102 — Accepted Artifact限定Manuscript Export

| ファイル | 主な変更 | 公開契約 |
|---|---|---|
| `src/living_narrative/book/exporter.py` | accepted attemptだけを原稿化するdomain exporter | `IncompleteManuscriptError`、`ManuscriptExportResult`、`export_accepted_manuscript()` |
| `src/living_narrative/cli/export.py` | `export manuscript` subcommand | `living-narrative export manuscript` |
| `tests/book/test_exporter.py` | 本文・manifest・未accept拒否の検証 | exporter回帰 |
| `tests/cli/test_export_command.py` | 既存export CLIとの互換性 | CLI回帰 |

#### Python API

```python
class ManuscriptExportResult(BaseModel):
    manuscript_path: Path
    manifest_path: Path
    chapter_count: int

export_accepted_manuscript(
    workspace_root: Path,
    output_dir: Path,
) -> ManuscriptExportResult
```

BookPlan順に各章を処理し、`BookLedger`が`accepted`であることと、lineageに`accepted_attempt_id`があることを両方検証します。いずれかが欠ければ`IncompleteManuscriptError`となり、未検証本文は出力しません。

#### CLI

```bash
living-narrative export manuscript \
  --project /path/to/project.yaml \
  --output /path/to/export-directory
```

`--output`未指定時は`workspace/exports/manuscript`を使用します。出力は次の二つです。

```text
{output_dir}/manuscript.md
{output_dir}/manuscript_manifest.yaml
```

manifestにはBookPlan順の`chapter_id`、`attempt_id`、`candidate_sha256`と、全原稿のSHA-256が保存されます。本文のatomic writeとmanifestのatomic writeを別々に行います。

---

### Issue 103 — 長編Benchmark Harness

| ファイル | 主な変更 | 公開契約 |
|---|---|---|
| `src/living_narrative/book/benchmark.py` | path-free、read-only benchmark observation/report | `BookBenchmarkObservation`、`benchmark_book()`、`write_book_benchmark_report()` |
| `tests/book/test_benchmark.py` | JSON schema、path/prompt非開示、fingerprintの検証 | benchmark回帰 |
| `docs/issues/103-long-form-benchmark-harness.md` | 受入条件・運用範囲 | Issue仕様 |

#### Python API

```python
class BookBenchmarkObservation(BaseModel):
    name: str
    planned_chapters: int
    accepted_chapters: int
    revising_chapters: int
    blocked_chapters: int
    attempt_count: int
    open_thread_count: int
    artifact_fingerprint: str  # 64桁hex SHA-256

benchmark_book(workspace_root: Path, *, name: str) -> BookBenchmarkObservation
write_book_benchmark_report(
    path: Path,
    observations: Sequence[BookBenchmarkObservation],
) -> Path
```

`benchmark_book()`はworkspaceを変更しません。`blocked_chapters`は`review`または`revising`の章数です。fingerprintはBookPlanの章順、各章のattempt identity、accepted attempt、およびcandidate hashから決定的に生成されます。

`write_book_benchmark_report()`はnameの重複を`ValueError`で拒否し、次の形式のJSONをatomicに書込みます。

```json
{
  "schema_version": 1,
  "books": [
    {
      "name": "fixture-a",
      "planned_chapters": 30,
      "accepted_chapters": 12,
      "revising_chapters": 2,
      "blocked_chapters": 4,
      "attempt_count": 19,
      "open_thread_count": 7,
      "artifact_fingerprint": "<64-digit-sha256>"
    }
  ]
}
```

benchmark reportは本文、prompt、認証情報、絶対パスを含みません。現状はPython APIであり、`living-narrative book benchmark` CLIは次期拡張です。

## 3. 横断的変更ファイル

| ファイル | 097〜103への関与 |
|---|---|
| `src/living_narrative/book/coordinator.py` | proposal適用、chapter lifecycle、artifact/lineage/continuityをtransaction境界で統合 |
| `src/living_narrative/book/drafting.py` | recoverable run、budget preflight、continuity digestのprompt投入 |
| `src/living_narrative/book/review.py` | semantic continuity assessment、blockによるrevise判定 |
| `src/living_narrative/book/chapters.py` | reader-safe ChapterContextとcontinuity digest投影 |
| `src/living_narrative/state/models.py` | BookLedgerのcontinuity schema |
| `src/living_narrative/web/page.py` | Cockpit読み込み、lifecycle badge、start/accept/reviseのfetch UI |
| `docs/issues/097…103*.md` | 受入条件、非対象、実装完了記録 |

## 4. 例外・整合性・安全性の早見表

| 層 | 代表的な失敗 | 観測・回復方法 |
|---|---|---|
| lineage | artifact欠落/hash不一致、重複candidate | `ValueError`/`FileExistsError`。既存attemptは変更しない。 |
| review/accept | semantic block、acceptでないreview、不正lifecycle | coordinatorが拒否。HTTPでは409。 |
| drafting/budget | chapter/book/revision上限超過 | providerを呼ばず`BudgetExceededError`と`circuit_breaker.yaml`。 |
| exporter | 未accept章、accepted pointer欠落 | `IncompleteManuscriptError`。原稿出荷を中止。 |
| benchmark | observation名重複 | `ValueError`。workspaceの状態は変更しない。 |
| Web | lock競合、権限不足、無効遷移 | project access gate、409応答、UI再読込。 |

## 5. テスト対象

今回の変更は、`test_lineage.py`、`test_continuity.py`、`test_budget.py`、`test_exporter.py`、`test_benchmark.py`、`test_chapter_compilation.py`、`test_chapter_production_coordinator.py`、`test_book_cockpit_api.py`、`test_web_app.py`を中心に回帰固定されています。最終時点の全回帰結果は**1107 passed / 2 skipped**です。
