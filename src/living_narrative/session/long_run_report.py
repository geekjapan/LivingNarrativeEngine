"""Public, comparison-friendly reports for deterministic long-run smoke journeys.

The report intentionally contains no absolute workspace path, timestamp, prompt, or
provider configuration.  It is an observability artifact for CI and local release
engineering, not a second source of narrative state.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from living_narrative.session.metrics import ProjectMetrics


@dataclass(frozen=True)
class LongRunObservation:
    """One completed long-run journey's public aggregate measurements."""

    name: str
    turn_count: int
    elapsed_seconds: float
    workspace_artifact_bytes: int
    replay_bytes: int
    run_fingerprint: str
    metrics: ProjectMetrics

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("journey name must not be empty")
        if self.turn_count < 0:
            raise ValueError("turn count must not be negative")
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed seconds must not be negative")
        if self.workspace_artifact_bytes < 0:
            raise ValueError("workspace artifact bytes must not be negative")
        if self.replay_bytes < 0:
            raise ValueError("replay bytes must not be negative")
        if len(self.run_fingerprint) != 64:
            raise ValueError("run fingerprint must be a SHA-256 hex digest")

    def public_payload(self) -> dict[str, object]:
        """Return only data that is safe to publish as CI diagnostics."""
        return {
            "name": self.name,
            "turn_count": self.turn_count,
            "elapsed_seconds": self.elapsed_seconds,
            "workspace_artifact_bytes": self.workspace_artifact_bytes,
            "replay_bytes": self.replay_bytes,
            "run_fingerprint": self.run_fingerprint,
            "metrics": self.metrics.model_dump(mode="json"),
        }


def write_long_run_report(path: Path, observations: Sequence[LongRunObservation]) -> Path:
    """Write a stable-schema JSON report and return its path.

    Measured duration is intentionally the only run-varying field.  The function
    does not inspect a workspace and therefore cannot serialize private state,
    prompts, credentials, or absolute filesystem paths by accident.
    """
    names = [observation.name for observation in observations]
    if len(names) != len(set(names)):
        raise ValueError("journey names must be unique")

    payload = {
        "schema_version": 1,
        "journeys": [observation.public_payload() for observation in observations],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
