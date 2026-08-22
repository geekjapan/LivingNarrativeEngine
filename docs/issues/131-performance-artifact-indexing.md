---
id: 131
title: 100章規模のPerformance/Artifact Indexingを実装する
status: completed
created: 2026-08-21
type: feature
priority: P1
parent: 131
blocked_by: [129, 130]
labels: [long-form, production, performance, benchmark, indexing, privacy]
---

# 131: 100章規模のPerformance/Artifact Indexingを実装する

## 背景

Cockpit、benchmark、export planningがchapterごとのrun artifactを毎回全走査すると、100章規模で運用許容時間を超える。cacheは正本ではなく、miss・削除・worker restartが正しさを変えないreader-safe indexとして導入する必要がある。

## 公開seam

`ensure_book_artifact_index(workspace) -> BookArtifactIndex`は、reader-safe metadata indexを取得する最適化seamである。`load_book_artifact_index(workspace)`はcanonical JSON SHA-256の不整合をfail closedし、`ensure_*`は欠損または不正なcacheをauthoritative artifactsから再構築する。indexはBook Stateの正本ではない。

`benchmark_book(workspace, name)`はread-onlyのduration測定を`BookBenchmarkObservation.duration_ms`へ記録する。`write_book_benchmark_report(..., slo=...)`はschema v3のreader-safe reportへ閾値と評価結果を記録し、CLIの`--max-duration-ms`はreport保存後に品質gateとして失敗する。

## 完了条件

- [x] deterministic 100章fixtureを`create_benchmark_fixture.py --chapters 100`で生成できる。
- [x] 100章fixtureのbenchmark fingerprintをversioned baselineとして固定し、CIで継続比較する。
- [x] provider非呼出の100章benchmarkを、CI環境に耐える`10,000 ms`の明示SLOでquality gateする。
- [x] reader-safe benchmark fingerprintとplanned chapter countだけをatomic indexとして保存・再読込できる。
- [x] reader-safe run/lineage/publication metadataを追加索引化し、本文、prompt、credential、private context、absolute pathを保存しない。
- [x] index更新はcanonical JSON SHA-256のatomic publishを用い、partial writeまたはhash不整合時はloadをfail closed、ensureをartifact再読込する。
- [x] cache missまたはindex削除時に、authoritative artifactsから同じpublic fingerprint indexを再構築できる。
- [x] worker restart相当のbuild後loadでもpublic結果が同一であることを回帰テストで固定する。
- [x] SLO測定をschema v3 benchmark reportへ追加し、100章fixtureの閾値超過をCIで検出する。

## SLO根拠と適用範囲

2026-08-22の開発環境で、provider非呼出の100章fixtureに対するbenchmark本体の観測値は約**35 ms**、CLI外形は約**270 ms**であった。`10,000 ms`はこの局所計測値を性能目標として固定する値ではなく、共有CIの起動・I/O揺らぎを許容しつつ、桁違いの回帰を検出する保守的なquality gateである。

このSLOが対象にするのは、Book State・lineage・durable production runを読む**provider非呼出benchmarkのread-only処理**だけである。実LLMの応答時間、著者レビュー時間、本文品質、queue workerの実行時間をこの閾値で評価してはならない。実行時間を含むoperations alert候補はIssue 132のreader-safe aggregateを用いる。

## 非対象

indexをBook Stateの正本にすること、本文検索、embedding/vector database、private contextの索引化は対象外である。実LLMを含むend-to-end latencyのSLOと外部通知サービスも対象外である。
