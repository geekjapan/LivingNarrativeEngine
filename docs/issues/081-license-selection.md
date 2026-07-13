---
id: 081
title: LICENSEを選定し配置する
status: open
created: 2026-07-13
type: implementation
priority: P1
parent: 059
blocked_by: []
---

# 081: LICENSEを選定し配置する

Issue 059の決定(2026-07-13承認)とIssue 062のDAGに基づく実装Issue。

## 完了条件

- **人間決定**: MIT(最小)かApache-2.0(特許明確)を選定する。depsは全て許容的で制約なし。
- LICENSE file配置+`pyproject.toml`のlicense欄追記。
- 生成コンテンツの権利はコードlicense対象外である旨を`docs/rights-and-security.md`と整合させる。

## 関連ファイル

- `LICENSE`(新規)、`pyproject.toml`
- `docs/rights-and-security.md`
