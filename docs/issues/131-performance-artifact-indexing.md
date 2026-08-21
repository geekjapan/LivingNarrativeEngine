---
id: 131
title: 100章規模のPerformance/Artifact Indexingを実装する
status: in-progress
created: 2026-08-21
type: feature
priority: P1
parent: 131
blocked_by: [129, 130]
labels: [long-form, performance, benchmark, indexing]
---

# 131: 100章規模のPerformance/Artifact Indexingを実装する

## 背景

Cockpit、benchmark、export planningがchapterごとのrun artifactを毎回全走査すると、100章規模で運用許容時間を超える。cacheは正本ではなく、miss・削除・worker restartが正しさを変えないreader-safe indexとして導入する必要がある。

## 公開seam

`build_book_artifact_index(workspace) -> BookArtifactIndex`と`load_book_artifact_index(workspace) -> BookArtifactIndex`を候補seamとする。Cockpit、benchmark、publication planningはindexを最適化として読むが、index不在またはhash不整合ではartifact正本へfallbackする。

## 完了条件

- [x] deterministic 100章fixtureを`create_benchmark_fixture.py --chapters 100`で生成できる。
- [ ] status/benchmark/export planningの基準値とSLOをv0.3.1 baselineから固定する。
- [x] reader-safe benchmark fingerprintとplanned chapter countだけをatomic YAML indexとして保存・再読込できる。
- [ ] reader-safe run/lineage/publication metadataを追加索引化し、本文、prompt、credential、private contextを保存しない。
- [ ] index更新はevent-first/atomic publishで、partial writeまたはhash不整合時にfail closedまたはartifact再読込する。
- [x] cache missまたはindex削除時に、authoritative artifactsから同じpublic fingerprint indexを再構築できる。
- [ ] worker restartでpublic結果が変わらないことを回帰テストで固定する。
- [ ] SLO測定をbenchmark reportへ追加し、閾値超過をCIで検出する。

## 初期観測

2026-08-21の開発環境では、`create_benchmark_fixture.py --chapters 100`で作成したprovider非呼出fixtureに対し、`book benchmark`は100 planned chapters・0 production runsをreader-safe reportへ出力し、wall-clock **632 ms** で完了した。この値はSLOではなく、CI環境でのrepeatableな閾値とartifact index導入後の比較基準を定義するための初期観測である。

## 非対象

indexをBook Stateの正本にすること、本文検索、embedding/vector database、private contextの索引化は対象外である。
