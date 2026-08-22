"""Release evidence commands that delegate to reader-safe engine validation."""

from pathlib import Path

import typer

from living_narrative.cli._common import usage_error
from living_narrative.release_evidence import (
    RealLLMBenchmarkValidation,
    validate_real_llm_benchmark_artifact,
)

app = typer.Typer(no_args_is_help=True)


@app.command("verify-real-llm-evidence")
def verify_real_llm_evidence(
    artifact: Path = typer.Option(..., "--artifact", help="Path to benchmark.json"),
    expected_revision: str = typer.Option(
        ..., "--expected-revision", help="Release candidate Git revision"
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit reader-safe JSON"),
) -> None:
    """Validate a saved real-LLM benchmark artifact without modifying it."""
    if not artifact.is_file():
        usage_error(f"artifact not found: {artifact}")

    validation = validate_real_llm_benchmark_artifact(artifact, expected_revision)
    if json_output:
        typer.echo(validation.model_dump_json())
    else:
        typer.echo(_format_validation(validation))

    if not validation.passed:
        raise typer.Exit(code=1)


def _format_validation(validation: RealLLMBenchmarkValidation) -> str:
    status = "PASS" if validation.passed else "FAIL"
    reason_codes = ",".join(validation.reason_codes) or "none"
    observed_revision = validation.observed_revision or "missing"
    return "\n".join(
        [
            f"result: {status}",
            f"reason_codes: {reason_codes}",
            f"completed_turns: {validation.completed_turns}",
            f"expected_revision: {validation.expected_revision}",
            f"observed_revision: {observed_revision}",
        ]
    )
