---
id: 051
title: ClaudeとCodexのプロジェクト指示を共通化する
status: done
created: 2026-07-11
---

# 051: ClaudeとCodexのプロジェクト指示を共通化する

## 背景

`AGENTS.md`が初期状態のJavaScript/TypeScript構成を説明する一方、実際のPython固有ルールが`CLAUDE.md`だけに偏っていた。共有エージェント設定に合わせ、両モデルが同じプロジェクト固有指示を読む構成にする。

## 完了条件

- [x] `AGENTS.md`を現行アーキテクチャ、Issue/ADR運用、必須契約、検証コマンドに限定する
- [x] `CLAUDE.md`を`AGENTS.md`のimportだけにする
- [x] 新規作業ではOpenSpecを使わず、既存spec/archiveを凍結参照として維持する
- [x] GitNexus再索引がagent instructionへ自動注入しないコマンドを記載する
- [x] ClaudeとCodexの双方でproject instructionの読込みを確認する
- [x] 全test、ruff、diff checkがpassする

## 関連ファイル

- `AGENTS.md`
- `CLAUDE.md`
