# 長編試作評価：『煤の王冠と玻璃の書架』第1章

> **判定**：現行エンジンは、Story Bibleからの計画、候補artifact、長さgate、改稿、transaction-backed承認までを一章単位で実証できた。一方で、数十万文字級の自律商業制作を主張できる段階ではない。次の実装は、本文生成をエンジン内の回復可能なrunとして扱い、連続性・改稿履歴・予算を管理することに集中する。

## 試作条件

| 項目 | 内容 |
| --- | --- |
| 作品 | 『煤の王冠と玻璃の書架』 |
| ジャンル | 異世界転生ファンタジー、政治劇、叙情的 |
| 計画 | 3 act・9 chapter。第1章の目標範囲は 3,500–5,500 body units |
| 第1章の義務 | 再誕、書庫、飢饉帳簿の矛盾、警告、主人公の他者配慮の癖 |
| 生成モデル | `gpt-5`。本文はプロンプト・usageとともに保存 |
| 承認経路 | BookPlan proposal → BookLedger lifecycle → candidate/review artifact → transaction journal → accept |

## 実測結果

| 試行 | 生成文字数 | gate計測値 | 判定 | LLM completion tokens | 主要所見 |
| --- | ---: | ---: | --- | ---: | --- |
| 初稿 | 7,520 | 6,481 | revise | 8,387 | 上限5,500を超過。長さ以外は判定不能 |
| 改稿 | 4,982 | 4,433 | accept | 6,807 | 目標範囲に収まり、長さgateを通過 |

初稿は明示した文字数制約にもかかわらず上限を超過した。現行の決定的quality gateがこれを確実に検出し、`revising` に留めた点は正しい。改稿では上限を小さくした出力budgetと、具体的な削減要求を組み合わせた結果、範囲内に収まった。改稿candidateは本文hashをjournal識別子に含めるため、以前のcandidate/review transactionを再利用せず、`candidate → review → accepted` を新規に記録できた。

## 今回実装した修正

Chapter production coordinatorを追加し、`planned → running → candidate → review → accepted/revising` をStateDiffとproject lockを経由して更新できるようにした。candidateとreviewをcommit前artifactとして保存し、改稿candidateは本文hashに基づく個別journalを用いる。これにより、改稿時に古いcandidate transactionがrecovery conflictを起こす問題を回避する。

| 失敗モード | 対策 | 回帰テスト |
| --- | --- | --- |
| candidate artifactとledger更新の片方だけが残る | commitの`on_commit`内でartifactを保存 | lifecycleの正常系 |
| 改稿candidateが旧journalと衝突する | candidate本文hashをjournal keyに使用 | revision candidateの独立journal |
| 無効なstate遷移 | `BookLedgerState.transition()`に委譲 | lifecycle validation既存契約 |
| long draftが受理される | deterministic length review | 初稿の`revise`、改稿の`accept` |

## 実測で判明した機能ギャップ

| 優先度 | ギャップ | 試作で確認された根拠 | 必要な実装 |
| --- | --- | --- | --- |
| P0 | engine内のchapter drafting runがない | 生成は外部補助scriptで実行した | `ChapterDraftRun`、prompt snapshot、model binding、retry、run status、recovery |
| P0 | 品質gateが長さ中心 | 初稿は長さだけで判断された | beat coverage、必須thread、視点、人物一貫性、禁則、継続性rubric |
| P0 | revision attemptの正本履歴がない | 現在のchapter artifactは最新candidateを投影する | immutable attempt manifest、accepted artifact pointer、比較可能なrevision lineage |
| P1 | 章間コンテキスト圧縮がない | 9章以上で過去本文がpromptを圧迫する | rolling summary、thread/arc ledger、reader-visible continuity digest |
| P1 | 予算・停止統治がない | 2回の試行で15,590 completion tokensを消費 | chapter/run/book予算、retry上限、quality failure circuit breaker |
| P1 | Web画面は設計段階 | コックピットはモックアップのみ | read API、mutation API、権限gate、UI contract test |
| P2 | manuscript exportがない | accepted chapterを読者向け原稿へ束ねられない | manifest付きMarkdown/EPUB/DOCX export、再現可能な目次 |
| P2 | 商業品質benchmarkがない | 一章の成功は長編品質を示さない | 複数Bible、30/90/200章試験、editor rubric、cost/latency dashboard |

## 次の実装ロードマップ

| Wave | Issue | 成果物 | 完了条件 |
| --- | --- | --- | --- |
| 5A | 096 | `ChapterDraftRun` とrun artifact | 1章の生成・retry・recoveryがCLI/APIから再開可能 |
| 5B | 097 | attempt manifestとrevision lineage | すべての候補・review・accept理由を破壊せず追跡可能 |
| 5C | 098 | semantic chapter gate | 目標beat、thread、視点、連続性を根拠つきでblock/revise |
| 6A | 099 | rolling summaryとcontinuity ledger | 20章試作で必要コンテキストが上限内、過去設定の矛盾を検出 |
| 6B | 100 | budget/circuit-breaker | chapter・bookの費用、retry、停止理由を明示的に管理 |
| 7A | 101 | Web cockpit実装 | 章の状態、品質block、次操作、承認を一画面で安全に操作可能 |
| 7B | 102 | exporter/manifest | accepted artifactのみを完全な原稿へ変換・再生成可能 |
| 8 | 103 | 長編benchmark harness | 代表3作品で30章以上の品質・コスト・復旧指標を継続測定 |

## 商業品質に達したと判断する条件

商業品質はLLMの一回の文章評価で判定しない。少なくとも、複数の代表Story Bibleに対する30章以上の連続制作、すべてのaccept artifactの再現可能なprovenance、必須プロット義務と連続性の未解決blockがゼロ、定義済みの予算内での停止・再開、編集者によるブラインド評価、そしてexported manuscriptの検証を満たす必要がある。数十万文字級へ拡大するのは、この30章試験を安定して通過してからとする。
