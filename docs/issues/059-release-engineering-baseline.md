---
id: 059
title: CI・package・Dockerのrelease engineering基準を決定する
status: done
created: 2026-07-12
type: wayfinder:research
priority: P1
parent: 052
blocked_by: []
---

# 059: CI・package・Dockerのrelease engineering基準を決定する

## 問い

対応Python、dependency lock、web extra、wheel、Docker、upgrade、license、versioning、security scanをどのmatrixで継続検証し、1.0 artifactとして何を配布するか。

## 背景

localでは951 testsがpassするが、CIは`uv sync`のみでoptional web extraをinstallせず、84件のWeb testがclean環境でskipされ得る。Python 3.12最低版のmatrix、wheel install smoke、実Docker health、coverage/type/security gate、LICENSE／changelog／release workflowがない。FastAPI TestClientにもdeprecation warningがある。

## 解決条件

- Python 3.12と最新対応版、web有無、OSのsupport matrixを決める
- `uv sync --frozen --extra web`、skip policy、wheel build/install、Docker smokeを決める
- coverage、type check、dependency／container／taint scanの採否と閾値を決める
- versioning、license、changelog、release artifact、upgrade policyを決める
- clean machineでのquickstart／backup restore／migration検証を定義する
- βschema凍結の宣言形式(git tag／文書)を決める(ADR-0005 D2/D4の保証起点発効)

## 関連ファイル

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `uv.lock`
- `Dockerfile`
- `compose.yml`
- `README.md`
- `tests/test_docker_quickstart.py`


## 決定(2026-07-13承認済)

事実確認: 背景の一部はstale — CIは既に`uv sync --extra web`実行済(`ci.yml:15`)で84 web test+journeyはCIで走っている。実ギャップ=(1)`--frozen`不使用(lockドリフトが緑で通る)、(2)web extra破損時に84+1 testが全skipのままCI緑=α gate信号の偽装リスク(全fileがmodule-level importorskip)、(3)wheel/実Docker smoke不在(`test_docker_quickstart.py`は静的検証のみ、HEALTHCHECKなし)、(4)coverage/type/security gate皆無、(5)LICENSE/CHANGELOG/release workflow不在。SemVerはADR-0006で確定済(新規決定不要)。schema_version=1が現行βschema候補(migrations登録0件)。

### 決定

- (a) **support matrix**: ubuntu-latestのみ×3 job — test-min(3.12+web)/test-max(3.13+web)/test-core(3.12 extra無し、CLI単体+skip正当性)。macOS/WindowsはCI外(release前手動macOS smoke任意)。3.14はpost-1.0。
- (b) **CI強化**: `uv sync --frozen --extra web`化(must)/web-extra import guard=pytest前に`python -c "import fastapi, uvicorn"`でskip偽装を即失敗化(must)/wheel build→fresh venv install→CLI起動smoke(専用job)/Docker `compose build→run init→up→curl /api/projects→down` smoke(must、βの2経路clean install smokeの実体)。
- (c) **scan採否**: coverage=report-only採用(閾値gateなし)/type check=不採用(post-1.0)/pip-audit=release時must・PR時advisory/container scan=不採用(post-1.0)/taint自動gate=不採用(disclosure契約はbehavior testで強制済+手動/security-review)。
- (d) **versioning=SemVer(ADR-0006正本、明文化のみ)**。license=**人間決定**(deps全て許容的で選択自由。permissive自然、特許明確性ならApache-2.0、最小ならMIT)。changelog=Keep a Changelog形式手動運用、schema_version bumpと紐付け。release artifact=git tag `v1.0.0`+wheel/sdist(GitHub Release添付)+tagged Dockerfile local build。**PyPI/registry pushはpost-1.0**。upgrade=`git pull`+`uv sync`+自動migration、patchはschema不変。
- (e) **clean machine検証**: 専用プロビジョニングは作らずCI runner=clean環境として1つの「clean-install acceptance」jobに集約(wheel install+journey E2E/backup→改変→restore一致smoke/βschema fixture load harness)。
- (f) **βschema凍結宣言=doc(ADR)+git tag併用**: ADRに「βschema=schema_version 1 @ commit <sha>」+保証scope明記、annotated tag(`beta-schema-v1`)を同commitへ。migration regression fixtureをtagへpin。

### ADR候補

- **ADR: License選定**(人間決定ブロック — 再licenseは不可逆)
- **ADR: Release engineering baseline** — release artifact定義・CHANGELOG運用・upgrade policy・βschema凍結宣言形式。CI戦術(matrix構成・scan採否)は可逆なのでADRに入れない

### 実装Issue分割

- A(P1): CI hardening(--frozen/matrix/import guard/filterwarnings)
- B(P1): packaging+clean-install acceptance(wheel/Docker/backup-restore/migration harness)
- C(P1): pip-audit+coverage report
- D(P2、人間gate): LICENSE選定+配置
- E(P1): release契約doc+CHANGELOG+checklist+βschema凍結宣言(ADR承認後)
