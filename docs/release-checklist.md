# Release checklist

この文書は、ADR-0005（1.0リリース契約）、ADR-0006（stability tier）、ADR-0011
（release engineering baseline）に従って、βおよび1.0の出荷判定を記録するための
契約文書である。各項目は証跡のパスまたはURLを併記し、未確認・証跡なしは未達として
扱う。

## バージョンと互換性の契約

- バージョン番号はSemVer 2.0.0（`MAJOR.MINOR.PATCH`）を使う。
- stableとして保証する公開面は、ADR-0005 D1/D2のinstall・`init`・`serve`・
  `export`の代表journey、project schemaとmigration、CLIの公開引数、export形式、
  allowlist設定形式とtransactional登録、provider設定面（`base_url`・`model`・
  key環境変数・mock provider指定）である。
- stable面の互換性を破る変更はmajor、後方互換な機能追加はminor、互換性を保つ修正は
  patchとする。patchではschema_versionを変更しない。
- plugin SDK Python APIと自作provider protocolはexperimentalであり、minorで変更
  され得る。experimental面の変更をstable面のtrust boundaryや秘密情報保護の弱体化に
  利用してはならない。
- データ損失、replay再現性破壊、disclosure漏洩、allowlist外pluginのloadは、回避策の
  有無にかかわらずrelease blockerである（ADR-0005 D3）。

## Upgrade policy

1. upgrade前にprojectをbackupし、実行中のturnがないことを確認する。
2. Git経路は`git pull`後に`uv sync --frozen --extra web`を実行する。core-only利用時は
   `uv sync --frozen`を使う。
3. Docker経路は`docker compose pull`または`docker compose build`後に起動する。
4. 起動時に既存projectの`schema_version`を検査し、対応するmigrationを自動適用する。
   migrationは永続化する前に検証され、対応できないfuture versionはfail closedする。
5. βschema以降（`schema_version: 1`）のprojectは1.0まで自動migrationを保証する。
   βschemaより前のprojectはbest-effortであり、保証対象外とする。
6. βschema凍結後のschema変更は、必ずschema_versionを更新し、migration、regression
   fixture、CHANGELOG entryを同じ変更に含める。

## β gate

- [ ] α gate（全test green、mock providerによる代表journey E2E）がpassしている。
- [ ] `uv sync --frozen --extra web`によるUbuntu Python 3.12/3.13 clean installがpassしている。
- [ ] core-only clean installとCLI smokeがpassしている。
- [ ] wheelをfresh venvへinstallするsmokeがpassしている。
- [ ] Docker composeのbuild・`init`・起動・API smoke・停止がpassしている。
- [ ] backup→restore一致smokeがpassしている。
- [ ] βschema fixtureのload/migration harnessが`beta-schema-v1`へpinされている。
- [ ] ADR-0011に`schema_version 1 @ commit b17f72a289cada0170e00a10ee9222a8057063e0`と保証scopeがある。
- [ ] 同じcommitを指すannotated tag `beta-schema-v1`が存在する。
- [ ] Issue 072手順による実LLM 30ターン人手smokeが、Issue 073 rubricでpassしている。

## 1.0 gate

- [ ] β gateが全項目passしている。
- [ ] ADR-0005 D3のmust（journey完走、データ保全、replay、disclosure、plugin trust boundary）が全てpassしている。
- [ ] βschema→1.0 migration regressionがpassしている。
- [ ] Issue 070–072のSLO・実LLM品質gateがpassしている。
  - FAIL証跡: `docs/evaluations/2026-07-14-20260714-issue085-gpt56-luna-low-v2-benchmark.md`
    （30/30完走、pacing/thread SLOとhuman rubric R1/R3/R5が不合格、Issue 085）。
- [ ] Issue 076のUX受入と人手2セッションがpassしている。
- [ ] `pip-audit`のrelease時blocking checkがpassしている。coverageはreport-onlyで記録する。
- [ ] LICENSEが選定・配置済みである（Issue 081）。
- [ ] `CHANGELOG.md`にリリース内容、日付、比較対象が記録されている。
- [ ] package versionが`1.0.0`である。
- [ ] annotated tag `v1.0.0`、wheel、sdist、tagged Dockerfile local buildを確認している。
- [ ] GitHub Releaseへwheel/sdistを添付する。PyPI/registry pushはpost-1.0のため行わない。

## 実行する検証

```bash
NO_COLOR=1 uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

release artifactの追加確認は、CIのclean-install acceptance job（wheel、Docker、backup/
restore、βschema fixture）と、実LLM/UXの各証跡を参照する。βschema tagを作成する担当者は、
次のコマンドでannotated tagと対象commitを確認する。

```bash
git tag --annotate --message "Freeze beta schema v1" beta-schema-v1 b17f72a289cada0170e00a10ee9222a8057063e0
test "$(git rev-parse beta-schema-v1^{})" = "b17f72a289cada0170e00a10ee9222a8057063e0"
test "$(git cat-file -t beta-schema-v1)" = tag
```

このtagの作成・pushはrelease engineering操作であり、integration後にDispatcherが実施する。
