"""``living-narrative init``: create a new project + workspace from a minimal template."""

import re
import uuid
from pathlib import Path

import yaml

from living_narrative.state.models import ProjectConfig
from living_narrative.workspace.layout import MINIMAL_STATE_CONTENT, STATE_SUBDIRS


class InitDestinationExistsError(Exception):
    """Raised when the init output directory already exists and is not empty."""


def _slugify(title: str) -> str:
    ascii_title = title.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_title).strip("-").lower()
    return slug or "project"


def create_project(output_dir: Path, title: str) -> Path:
    """Create a new project at ``output_dir`` with a minimal empty-world workspace.

    Returns the path to the generated ``project.yaml``.
    """
    if output_dir.exists() and any(output_dir.iterdir()):
        raise InitDestinationExistsError(f"{output_dir} already exists and is not empty")

    project_data = {
        "id": _slugify(title),
        "title": title,
        "genre": "",
        "tone": "",
        "autonomy_level": "manual",
        "user_mode": "assistant_gm",
        "random_seed": uuid.uuid4().hex,
        "renderer": "novel",
        "llm": {"provider": "mock", "model": "mock-v1"},
        "workspace": {
            "root": "workspace",
            "state": "workspace/state",
            "runs": "workspace/runs",
            "exports": "workspace/exports",
        },
    }
    ProjectConfig.model_validate(project_data)

    output_dir.mkdir(parents=True, exist_ok=True)
    project_path = output_dir / "project.yaml"
    project_path.write_text(
        yaml.safe_dump(project_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    state_dir = output_dir / "workspace" / "state"
    for subdir in STATE_SUBDIRS:
        (state_dir / subdir).mkdir(parents=True, exist_ok=True)
    for filename, content in MINIMAL_STATE_CONTENT.items():
        (state_dir / filename).write_text(content, encoding="utf-8")

    (output_dir / "workspace" / "runs").mkdir(parents=True, exist_ok=True)
    (output_dir / "workspace" / "exports").mkdir(parents=True, exist_ok=True)

    return project_path
