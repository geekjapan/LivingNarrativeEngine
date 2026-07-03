"""Project read API: resolve workspace paths and check required state files.

This is the fast pre-check used by ``init``/``status`` etc. — it does not validate
state file *contents* (that is ``StateStore.load``'s job, added by add-state-model).
"""

from dataclasses import dataclass, field
from pathlib import Path

from living_narrative.state.models import ProjectConfig, WorkspaceConfig
from living_narrative.state.validation import ProjectValidationIssue, load_project_config
from living_narrative.workspace.layout import REQUIRED_STATE_FILES


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    state: Path
    runs: Path
    exports: Path


def resolve_workspace_paths(project_path: Path, workspace: WorkspaceConfig) -> WorkspacePaths:
    """Resolve ``workspace.*`` paths relative to the directory containing ``project_path``."""
    base = project_path.parent

    def resolve(raw: str) -> Path:
        path = Path(raw)
        return path if path.is_absolute() else base / path

    return WorkspacePaths(
        root=resolve(workspace.root),
        state=resolve(workspace.state),
        runs=resolve(workspace.runs),
        exports=resolve(workspace.exports),
    )


def missing_required_state_files(state_dir: Path) -> list[str]:
    return [name for name in REQUIRED_STATE_FILES if not (state_dir / name).is_file()]


@dataclass(frozen=True)
class ProjectReadResult:
    config: ProjectConfig | None
    paths: WorkspacePaths | None
    missing_state_files: list[str] = field(default_factory=list)
    errors: list[ProjectValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.config is not None and not self.errors and not self.missing_state_files


def load_project(project_path: Path) -> ProjectReadResult:
    """Load ``project.yaml``, resolve workspace paths, and check required state files exist."""
    report = load_project_config(project_path)
    if not report.is_valid:
        return ProjectReadResult(
            config=None, paths=None, errors=report.errors, warnings=report.warnings
        )

    paths = resolve_workspace_paths(project_path, report.config.workspace)
    missing = missing_required_state_files(paths.state)
    return ProjectReadResult(
        config=report.config,
        paths=paths,
        missing_state_files=missing,
        errors=report.errors,
        warnings=report.warnings,
    )
