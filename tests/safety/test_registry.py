import yaml

from living_narrative.safety.registry import (
    CheckRunResult,
    Finding,
    run_checkers,
    write_checks_yaml,
)


def test_checker_registry_resolves_registered_checker(monkeypatch):
    from living_narrative.safety import registry

    monkeypatch.setitem(
        registry.CHECKERS,
        "unit",
        lambda context, narration, events, diff: [
            Finding(checker="unit", severity="info", message="ok", related_ids=["x"])
        ],
    )

    result = run_checkers(None, "", [], None, names=["unit"])

    assert result.findings[0].checker == "unit"


def test_error_finding_blocks_auto_apply():
    result = CheckRunResult(findings=[Finding(checker="unit", severity="error", message="bad")])
    result.blocks_auto_apply = any(finding.severity == "error" for finding in result.findings)

    assert result.blocks_auto_apply is True


def test_warn_finding_does_not_block_auto_apply():
    result = CheckRunResult(
        findings=[Finding(checker="unit", severity="warn", message="warn")],
        blocks_auto_apply=False,
    )

    assert result.blocks_auto_apply is False


def test_findings_persist_to_checks_yaml(tmp_path):
    result = CheckRunResult(
        findings=[Finding(checker="unit", severity="info", message="ok", related_ids=["id"])]
    )

    write_checks_yaml(tmp_path / "checks.yaml", result)

    saved = yaml.safe_load((tmp_path / "checks.yaml").read_text(encoding="utf-8"))
    assert saved["findings"][0]["related_ids"] == ["id"]
