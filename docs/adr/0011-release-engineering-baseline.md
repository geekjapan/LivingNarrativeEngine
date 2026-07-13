# ADR-0011: release engineering baseline とβschema凍結形式

## Context

CIは1 job(ubuntu、`uv sync --extra web`)のみで`--frozen`不使用。web extra破損時は84+1 testが
全skipのままCI緑となりα gate信号が偽装され得る。wheel/実Docker smoke、LICENSE、CHANGELOG、
release workflowは不在。SemVerはADR-0006で確定済(Issue 059)。

## Decision

1. **support matrix**: ubuntu-latest×3 job(3.12+web/3.13+web/3.12 core-only)。
   macOS/WindowsはCI外。`uv sync --frozen --extra web`を必須化。
2. **skip偽装防止**: web系jobはpytest前に`python -c "import fastapi, uvicorn"`を実行し、
   extra破損をskipでなく失敗にする。
3. **clean-install acceptance**: wheel build→fresh venv install→CLI起動smoke、
   Docker `compose build→run init→up→curl→down` smoke(βの2経路clean install smokeの実体)、
   backup→restore一致smoke、βschema fixture load harnessをCI runner上で実施。
4. **scan**: pip-audit=release時must/PR時advisory。coverage=report-only。
   type check・container scan・taint自動gateは不採用(post-1.0)。
5. **release artifact**: git tag `v1.0.0`+wheel/sdist(GitHub Release添付)+tagged Dockerfile
   local build。PyPI/registry pushはpost-1.0。CHANGELOGはKeep a Changelog形式の手動運用で
   schema_version bumpと紐付ける。upgrade=`git pull`+`uv sync`+自動migration。
6. **βschema凍結宣言=doc+git tag併用**: ADR追記(またはaddendum)に
   「βschema=schema_version 1 @ commit <sha>」と保証scopeを明記し、同commitへ
   annotated tag `beta-schema-v1`を付与する。migration regression fixtureはこのtagへpinする。
   凍結はADR-0008のmeta.yamlフィールド追加の確定後に行う。
7. **LICENSE**: 選定は人間決定(Issue 081)。depsは全て許容的で選択自由。

## Consequences

- α gate信号(mock journey E2E)はskip偽装から保護される。
- βschema凍結宣言の発効をもってADR-0005 D2の migration保証起点が成立する。
- CI戦術(matrix構成・scan採否)は可逆な運用判断であり、本ADRの改訂なしに調整できる。
