---
id: 046
title: web設定・モデルプロファイルUI
status: in_progress
created: 2026-07-11
---

# 046: web設定・モデルプロファイルUI

## 背景

LLM profiles/bindingsとIssue 045のモデル別価格はYAMLを直接編集すれば設定できるが、ローカルweb UIから安全に確認・更新する導線がない。既存のlocalhost限定web serverを維持しつつ、Pydantic境界検証とatomic writeを通した設定ページを追加する。

## 設計

1. `project.yaml` の `llm_profiles` / `llm_bindings` と、同階層の `pricing.yaml` を設定APIおよびwebページで閲覧・編集できるようにする。
2. 保存前にYAML構文とPydantic/価格型を境界で検証し、不正入力はファイルを変更せず明確なエラーとして返す。既存の `ProjectConfig` モデルを検証の正本として再利用し、モデル自体は変更しない。
3. 検証済みデータは既存store流儀のtemporary sibling + replaceによるatomic writeで保存する。
4. APIが操作するパスはproject root内の固定ファイルだけに限定し、path traversal入力を拒否するテストを追加する。web serverのloopback bind保証を維持する。

## 完了条件

- [ ] 設定ページでLLM profiles/bindingsとpricingを閲覧できる
- [ ] 有効な設定を編集・保存し、再読込できる
- [ ] 不正YAML・不正profile/binding・不正価格型を明確に拒否し、既存ファイルを変更しない
- [ ] 設定書込みAPIのpath traversalを拒否する回帰テストがある
- [ ] 書込みがatomicで、localhost bind固定の既存保証を壊さない
- [ ] 全テスト、ruff check、ruff format checkがpassする
- [ ] 無関係変更がなく、GitNexus `detect_changes` で影響範囲を確認している

## 関連ファイル

- `src/living_narrative/web/app.py`
- `src/living_narrative/web/service.py`
- `src/living_narrative/web/page.py`
- `src/living_narrative/state/models.py` (`ProjectConfig`、検証のみ)
- `src/living_narrative/state/store.py` (atomic write流儀)
- `src/living_narrative/llm/costs.py` (`pricing.yaml`形式)
- `tests/web/`, `tests/llm/`
