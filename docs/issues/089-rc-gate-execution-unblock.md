---
id: 089
title: RC gate再実行の実行環境ブロック解除（gateway起動とAPI key）
status: open
created: 2026-07-29
type: release-validation
priority: P1
parent: 088
blocked_by: []
labels: [human-action-required]
---

# 089: RC gate再実行の実行環境ブロック解除（gateway起動とAPI key）

## 背景

Issue 088の実LLM 30ターンgate再実行（run ID `20260729-issue088-rc-gate`）を開始しようと
したが、実行環境の2点でブロックした。run環境の準備自体は完了している。

判明した事実（2026-07-29）:

- エンジンは`src/living_narrative/state/transaction.py`が`fcntl`（POSIX専用、ADR-0008の
  flock契約）を無条件importするため、**Windowsネイティブでは起動不可**。実行はWSL
  （Ubuntu、mirrored networking）経由とする。Windowsネイティブ対応は1.0 scope外であり、
  必要になった時点で別Issueを起こす。
- WSL側Linux venvは`~/.venvs/lne`へ構築済み（`UV_PROJECT_ENVIRONMENT`でWindows側
  `.venv`と分離）。
- `sandbox/20260729-issue088-rc-gate/`はinit済みで、`project.yaml`にseed
  `issue-085-mist-station-v1`、model `cx/gpt-5.6-luna-low`、character_default+narratorの
  binding、`prompt_recording: hash_only`を設定済み（前回PASS runと同一契約）。

## ブロック（人間操作が必要）

1. **OmniRoute gatewayの起動**: `127.0.0.1:20128`がWindows/WSL両方から接続拒否。
   プロセスも存在しない。gatewayを起動する。
2. **`OPENAI_API_KEY`の設定**: Windows/WSLどちらの環境にも未設定。値をchatやファイルへ
   貼らず、WSL側shell環境へexportする。ローカルgatewayがdummy keyを許容する場合は
   その旨をagentへ伝えれば、placeholderで実行する。

## 完了条件

- [ ] WSLから`curl http://127.0.0.1:20128/v1/models`が200を返す。
- [ ] WSLのrun実行shellで`OPENAI_API_KEY`が設定されている（値は記録しない）。
- [ ] 30ターンrunを開始できる（開始後の実行・判定はIssue 088の完了条件）。

## 再開手順（agent向け）

ブロック解除後、次でrunを再開する。詳細は`docs/real-llm-benchmark.md`に従う。

```bash
# WSL内、repo root
export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/lne
RUN_DIR=sandbox/20260729-issue088-rc-gate
# turn 1-15を1ターンずつ実行 → プロセス終了 → 新shellでturn 16-30（resume経路）
# 各ターン: uv run living-narrative auto --project "$RUN_DIR/project.yaml" --turns 1
# pending_review/stopped_for_reviewはreview --decision accept_allで進める
# 完了後: metrics --json保存、git_revision.txt、benchmark.json/Markdown転記、SLO判定
```

## 関連ファイル

- `docs/issues/088-v1-release-closeout.md`
- `docs/real-llm-benchmark.md`
- `sandbox/20260729-issue088-rc-gate/project.yaml`
