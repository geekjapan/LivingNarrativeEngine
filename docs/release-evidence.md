# Release evidence ledger

この台帳は ADR-0005、ADR-0010、ADR-0011 と `docs/release-checklist.md` に従い、
β および 1.0 の出荷判定を、再実行可能な証跡とともに追跡する。

> `pass` は証跡が存在し、再実行手順が定義されていることを意味する。`pending` は
> 実装または検証が未完了であること、`blocked` は先行 gate の未達により判定不能で
> あることを意味する。証跡のない項目を `pass` としてはならない。

## 運用規約

- 実装変更時は該当行の status、証跡、再実行コマンドを同じ pull request で更新する。
- 実 LLM と UX の判定は、run ID、model/binding、prompt recording policy、評価者、
  rubric を `docs/evaluations/` に保存する。credential と private workspace は記録しない。
- CI が生成する 100-turn report は `long-smoke-<matrix>.json` artifact として保存する。
  report には絶対 path、prompt、API key、GM-only data を含めない。
- `pending` または `blocked` が 1.0 の must に一つでも残る場合、release は作成しない。

## β gate

| Gate | Status | 証跡 | 再実行 | 更新条件 |
|---|---|---|---|---|
| α: 全 test と mock representative journey | pending | CI `test-*` と `tests/smoke/test_mock_journey_e2e.py` | `NO_COLOR=1 uv run pytest` | 実行 commit、CI URL、結果を追記する。 |
| Web clean install (Python 3.12/3.13) | pending | CI `test-py312-web`、`test-py313-web` | `uv sync --frozen --extra web --group browser-test && NO_COLOR=1 uv run pytest` | matrix ごとの green run を記録する。 |
| Core-only clean install と CLI smoke | pending | CI `test-py312-core` | `uv sync --frozen && NO_COLOR=1 uv run pytest` | green run を記録する。 |
| Wheel fresh venv smoke | pending | CI `clean-install-acceptance` / `build wheel` / `wheel CLI smoke` | `.github/workflows/ci.yml` の該当 step | wheel hash と CI URL を記録する。 |
| Docker init/serve/API smoke | pending | CI `clean-install-acceptance` / `Docker Compose smoke` | `.github/workflows/ci.yml` の該当 step | image digest と CI URL を記録する。 |
| Backup/restore equality | pending | CI `clean-install-acceptance` / `backup modify restore equality smoke` | `.github/workflows/ci.yml` の該当 step | green run を記録する。 |
| β schema fixture と migration | pending | CI `clean-install-acceptance` / `beta schema fixture migration regression` | `uv run pytest tests/workspace/test_beta_schema_fixture.py` | tag と対象 commit を記録する。 |
| β schema annotated tag | pass | `beta-schema-v1` → `b17f72a289cada0170e00a10ee9222a8057063e0` | `git rev-parse beta-schema-v1^{commit}` | schema migration を追加した場合は再判定する。 |
| 実 LLM 30-turn / human rubric | pass | `docs/evaluations/2026-07-27-20260727-issue086-r4-hardening-benchmark.md` と同 human rubric | Issue 072 / 073 の手順 | provider/model/binding または物語挙動の変更時に再実行する。 |

## 1.0 gate

| Gate | Status | 証跡 | 再実行 | 更新条件 |
|---|---|---|---|---|
| β gate 全項目 | blocked | この台帳の β gate | 上表のすべて | β に `pending`/`blocked` が残る間は判定しない。 |
| journey、data preservation、replay、disclosure、plugin boundary | pending | CI、focused integration test、security scan | `NO_COLOR=1 uv run pytest`、`git diff --check` | public/state/plugin 面の変更ごとに再実行する。 |
| β schema → 1.0 migration | blocked | migration regression test | 新 version fixture を含む test | 1.0 schema version を確定後に実施する。 |
| 長期実 LLM SLO/品質 gate | pass | Issue 087 R4: 30/30 applied、resume、replay 1.0、leak 0、human rubric R1–R8 | Issue 072/073 の手順 | narration、pacing、state transition、LLM binding の変更時に再実行する。 |
| UX acceptance と人手2 session | pending | `docs/ux-acceptance-checklist.md` の記録 | checklist に従う | Web UI の public workflow 変更時に再実行する。 |
| pip-audit release blocking | pending | CI `security-quality` | `uv run --with pip-audit pip-audit` | release candidate ごとに実行する。 |
| LICENSE | pass | `LICENSE`、ADR-0012 | `test -f LICENSE` | license text を変更した場合に再判定する。 |
| CHANGELOG、version、tag、wheel/sdist、Docker | pending | release candidate | `uv build`、tagged Docker build | release candidate 作成時に実行する。 |
| GitHub Release attachment | blocked | release asset URL | release engineering 手順 | v1.0.0 tag 作成後に実施する。 |

## 100-turn long smoke observability

Issue 071 の permanent mock gate は同一 seed の二つの journey について、replay と
artifact fingerprint が一致すること、rollback、branch、resume、backup/restore、
pacing、thread、leak、encounter recurrence の契約を検査する。

`LNE_LONG_SMOKE_REPORT` を指定すると、成功時に次の JSON を保存する。

```bash
mkdir -p artifacts
LNE_LONG_SMOKE_REPORT=artifacts/long-smoke-local.json \
  NO_COLOR=1 uv run pytest tests/smoke/test_mist_station_100_turns.py
```

JSON schema version 1 の `journeys` は、journey name、turn count、elapsed seconds、
workspace artifact bytes、replay bytes、決定的 run fingerprint、公開可能な
`ProjectMetrics` だけを含む。duration と file size は計測値であるため実行ごとに変化
し得るが、同一入力の二 journey は `run_fingerprint` が一致しなければならない。
