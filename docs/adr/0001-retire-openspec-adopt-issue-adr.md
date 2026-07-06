---
id: ADR-0001
title: OpenSpecを新規作業から引退させ、Issue/ADR軽量プロセスに移行する
status: accepted
created: 2026-07-06
---

# ADR-0001: OpenSpec引退、Issue/ADRプロセス採用

## Context

Phase 1バッチ(OpenSpec change 9件)は2026-07-03に全実装・アーカイブ済み。アクティブなchangeはゼロで、プロセス切替の境界として最もきれいなタイミングだった。

今後の作業(ターン1実走で見つかった品質修正など)は数行〜1ファイル規模が中心で、OpenSpecのartifact workflow(proposal → design → specs → tasks → archive)はオーバーヘッドが実益を上回る。本リポジトリはサンドボックス探索環境であり、開発ギアをG3(仕様駆動)からG2(軽量ループ)へ下げる。

## Decision

- **OpenSpecは新規作業に使わない。** `openspec/specs/`(12 capability)と`docs/spec-foundation.md`は実装済み挙動の**凍結リファレンス**として残す。削除しない。今後の変更でspecと実装が乖離した場合、コードとテストが正。
- **作業単位はIssue**: `docs/issues/NNN-slug.md`。frontmatter(`id`/`title`/`status: open|in_progress|done`/`created`)+ 背景・完了条件・関連ファイル。
- **決定はADR**: `docs/adr/NNNN-slug.md`(Context / Decision / Consequences)。spec-foundation §9のD101–D122は有効なまま、新規決定はADR連番で継続する(D123以降は発番しない)。
- ループ: Issue起票 → 実装 → `/verify`(必要に応じ `/code-review`)→ status更新。

## Consequences

- 小さな修正の着手コストが大幅に下がる。
- 仕様と実装の同期保証は失われる — 挙動の正はコード+テストに移る。アーキテクチャ級の変更では、必要ならIssue内にspec相当の記述を厚めに書く。
- 既存のD101–D122の決定内容(state-first、diff経由の状態変更、visibilityモデル等)は本ADRによって効力を失わない。
