# Issue 088: 100-turn long smoke observability 実行記録

- 実行日: 2026-08-17
- 対象 commit: `3de4b7c` に Issue 088 の未commit変更を適用した worktree
- 実行環境: macOS / Python 3.13.13 / mock provider
- コマンド:

```bash
rm -f /tmp/lne-long-smoke-report.json
LNE_LONG_SMOKE_REPORT=/tmp/lne-long-smoke-report.json \
  NO_COLOR=1 uv run pytest tests/smoke/test_mist_station_100_turns.py
```

## 結果

| 項目 | 結果 |
|---|---:|
| pytest | PASS |
| 実行時間 | 185.67 秒 |
| journey 数 | 2 |
| 各 journey の turn 数 | 100 / 100 |
| journey-a elapsed | 92.415 秒 |
| journey-b elapsed | 91.837 秒 |
| replay / artifact fingerprint | 一致 |
| report schema version | 1 |
| report 内の絶対 `/tmp/` path | なし |

## 観測した契約

- report は `journey name`、turn count、elapsed seconds、workspace artifact bytes、
  replay bytes、run fingerprint、公開可能な metrics を持つ。
- 同一固定 seed の二 journey は、計測時間が異なっても run fingerprint が一致した。
- report は明示的な `LNE_LONG_SMOKE_REPORT` 指定時だけ書き込まれる。
- report の writer は workspace を探索しないため、prompt、credential、GM-only state、
  絶対 workspace path を偶発的に直列化しない。

## 注意

この記録は mock provider の性能・決定性証跡であり、実 LLM の品質 gate を置き換えない。
実 LLM に関する既存の品質根拠は Issue 087 の R4 evidence を参照する。
