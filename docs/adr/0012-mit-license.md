# ADR-0012: エンジンコードのlicenseをMITとする

## Context

1.0公開にはLICENSEの確定が前提となる(ADR-0011、Issue 081)。依存(openai/pydantic/
pyyaml/typer/fastapi/uvicorn)はすべて許容的licenseでcopyleft継承義務はなく、選択は自由。
persona=local単一利用者向けの趣味エンジンであり、AGPLのnetwork開示強制はadoptionを阻害する。
再licenseはcontributor同意を要する不可逆判断のためADRに記録する(人間決定: 2026-07-13)。

## Decision

- エンジンコードのlicenseは**MIT**とする(最小・permissive)。
- LICENSE fileをroot配置し、`pyproject.toml`へ`license = "MIT"`を記載する。
- licenseの対象はエンジンコードのみ。生成narrative・画像・音声等の成果物の権利は
  コードlicenseの対象外であり、`docs/rights-and-security.md`の規定に従う。

## Consequences

- 1.0 release checklist(Issue 080)のLICENSE項目が充足可能になる。
- 将来contributorを受け入れる場合も追加のCLA/特許条項なしで運用する
  (特許明確性が必要になった時点でApache-2.0への変更はcontributor同意が必要=事実上不可逆)。
