---
id: 118
title: v0.3.1 Benchmark CLI・fixture matrix・CI baselineを実装する
status: closed
created: 2026-08-21
type: feature
priority: P1
parent: 110
blocked_by: [117]
labels: [long-form, benchmark, ci, stabilization]
---

# 118: v0.3.1 Benchmark CLI・fixture matrix・CI baselineを実装する

## 背景

v0.3.0で章production runを実行・再開できるようになった。v0.4.0以降の品質・性能・費用判断を感覚的な成功例へ依存させないため、BookPlan、BookLedger、immutable lineage、durable run artifactを**read-only**に観測し、CIで比較できるpath-free benchmark reportを固定する必要がある。

## 公開seam

- `living-narrative book benchmark --project P --name N --output R`：一つのprojectをread-onlyに観測し、atomicなreader-safe JSON reportを出力する。
- `benchmark_book(...)`：既存のaggregateとfingerprint契約を維持しつつ、run phase・failure/budget/resumeの集計を追加する。
- CI long-smoke job：benchmark reportを生成・artifactとして保存し、baseline fingerprintを明示的に比較する。

## 完了条件

- [x] benchmark CLIがconfigurable workspace pathを尊重し、canonical stateを変更せずreportを出力する。
- [x] reportがBookPlan/BookLedger/lineage/production runのaggregateとfingerprintを含む。
- [x] reportが本文、prompt、credential、absolute path、GM/private dataを含まない。
- [x] 1章、9章、legacy BookPlan、budget stop、provider failure、resumeを含むfixture matrixを追加する。
- [x] CIがlong smokeとbenchmark reportをartifactとして保存し、expected fingerprintの差を検出する。
- [x] 2回の同一9章fixture測定を記録し、v0.4.0のperformance review用baselineを提示する。

## 実装結果

`living-narrative book benchmark`はprojectをread-onlyに観測してschema v2のpublic JSON reportをatomicに出力する。`--expect-fingerprint`を指定するとcombined benchmark fingerprintの差分をexit code 1で検出する。combined fingerprintは既存lineageのartifact fingerprintとdurable production run evidence fingerprintを合成するため、本文・prompt・credential・absolute path・failure detailをreportへ含めない。

CIはdeterministicな9章fixtureを生成し、`tests/fixtures/benchmark-v2-baseline.json`のfingerprintとの差分を確認したうえで、matrixごとのbenchmark reportをartifactとして保存する。baselineは同一fixtureのローカル2回測定で同一JSONとなることを確認した。

## Validation record

| Gate | 結果 |
|---|---|
| Fixture/CLI/domain focused | 14 passed |
| 全回帰 | `NO_COLOR=1 uv run pytest` — `1147 passed, 2 skipped in 231.15s` |
| Lint | `uv run ruff check .` — 成功 |
| Format | `uv run ruff format --check .` — 287 files already formatted |
| Diff integrity | `git diff --check` — 成功 |
| CI shell rehearsal | 9章fixture生成、baseline比較、report出力をlocalで成功 |

## 非対象

固定SLOのfail threshold、実LLMの費用測定、30章以上のhuman editorial rubric、persistent worker queueは本Issueに含めない。
