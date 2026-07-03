"""Load and validate ``project.yaml``, aggregating all errors (spec-foundation.md §5)."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from living_narrative.state.models import ProjectConfig


@dataclass(frozen=True)
class ProjectValidationIssue:
    path: Path
    field: str
    message: str


@dataclass(frozen=True)
class ProjectLoadReport:
    config: ProjectConfig | None
    errors: list[ProjectValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.config is not None and not self.errors


def load_project_config(path: Path) -> ProjectLoadReport:
    """Read and validate a ``project.yaml`` file, collecting every error at once."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    try:
        config = ProjectConfig.model_validate(raw)
    except ValidationError as exc:
        errors = [
            ProjectValidationIssue(
                path=path,
                field=".".join(str(part) for part in error["loc"]) or "<root>",
                message=error["msg"],
            )
            for error in exc.errors()
        ]
        return ProjectLoadReport(config=None, errors=errors)

    warnings = [
        f"Unknown field '{key}' in {path}; ignored for forward compatibility."
        for key in (config.model_extra or {})
    ]
    return ProjectLoadReport(config=config, warnings=warnings)
