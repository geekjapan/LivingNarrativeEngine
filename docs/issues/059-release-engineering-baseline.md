---
id: 059
title: CI・package・Dockerのrelease engineering基準を決定する
status: open
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

